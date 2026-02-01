#!/usr/bin/env python3
"""
CSI Software Statutory Filings Downloader

Scrapes and downloads statutory filings from Constellation Software Inc.'s
investor relations website: https://www.csisoftware.com/category/stat-filings

Works in both command-line and notebook (Colab/Jupyter) environments.
"""

import os
import re
import sys
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# Check if running in notebook
try:
    from IPython.display import display, HTML
    from google.colab import files as colab_files
    IN_COLAB = True
except ImportError:
    IN_COLAB = False


@dataclass
class Filing:
    """Represents a statutory filing document."""
    title: str
    url: str
    date: str
    pdf_urls: List[str] = field(default_factory=list)
    filing_type: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[str] = None


class CSIFilingsDownloader:
    """Download statutory filings from CSI Software website."""

    BASE_URL = "https://www.csisoftware.com"
    FILINGS_URL = f"{BASE_URL}/category/stat-filings"

    # Filing type patterns for classification
    FILING_TYPES = {
        "shareholder_report": ["shareholder", "shareholders report"],
        "financial_statements": ["financial statements", "financial report"],
        "mda": ["management discussion", "md&a", "mda"],
        "aif": ["annual information form"],
        "proxy": ["proxy", "circular"],
    }

    def __init__(self, download_dir: str = "csi_filings"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })

    def _classify_filing(self, title: str) -> Optional[str]:
        """Classify a filing based on its title."""
        title_lower = title.lower()
        for filing_type, patterns in self.FILING_TYPES.items():
            for pattern in patterns:
                if pattern in title_lower:
                    return filing_type
        return "other"

    def _extract_year(self, title: str, date: str) -> Optional[int]:
        """Extract the year from filing title or date."""
        # Try date first
        if date and date != 'unknown':
            year_match = re.search(r'20[0-9]{2}', date)
            if year_match:
                return int(year_match.group())
        # Try title
        year_match = re.search(r'20[0-9]{2}', title)
        if year_match:
            return int(year_match.group())
        return None

    def _extract_quarter(self, title: str) -> Optional[str]:
        """Extract the quarter from filing title."""
        quarter_match = re.search(r'q([1-4])', title.lower())
        if quarter_match:
            return f"Q{quarter_match.group(1)}"
        return None

    def get_all_pages(self) -> List[str]:
        """Get all pagination page URLs."""
        print("Fetching list of available pages...")
        try:
            response = self.session.get(self.FILINGS_URL, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching main page: {e}")
            return [self.FILINGS_URL]

        soup = BeautifulSoup(response.content, 'html.parser')
        pages = {1: self.FILINGS_URL}

        # Look for pagination links
        pagination_links = soup.find_all('a', href=re.compile(r'category/stat-filings/page/\d+'))

        for link in pagination_links:
            page_match = re.search(r'page/(\d+)', link['href'])
            if page_match:
                page_num = int(page_match.group(1))
                page_url = urljoin(self.BASE_URL, link['href'])
                pages[page_num] = page_url

        sorted_pages = [pages[num] for num in sorted(pages.keys())]
        print(f"Found {len(sorted_pages)} page(s) of filings")

        return sorted_pages

    def construct_pdf_urls(self, title: str, date: str) -> List[str]:
        """
        Construct possible PDF URLs from title.
        Returns a list of possible URLs to try.
        """
        title_lower = title.lower()
        possible_urls = []

        # Extract quarter and year from title
        quarter_match = re.search(r'q(\d)\s+(\d{4})', title_lower)
        if quarter_match:
            quarter_num = quarter_match.group(1)
            quarter = f"q{quarter_num}"
            year = quarter_match.group(2)
            year_short = year[2:]

            base_old = f"{self.BASE_URL}/docs/default-source/investor-relations/statutory-filings"
            base_new = f"{self.BASE_URL}/docs/default-source/press-releases"

            if 'shareholder' in title_lower:
                # Multiple URL patterns for shareholder reports
                possible_urls.extend([
                    f"{base_new}/{quarter}-{year}-shareholder-report.pdf",
                    f"{base_old}/{quarter}-{year}-shareholder-report.pdf",
                    f"{base_old}/csi-shareholder-report-{quarter}{year_short}.pdf",
                ])

            elif 'financial statements' in title_lower or 'financial report' in title_lower:
                possible_urls.extend([
                    f"{base_old}/csi-financial-statements-{quarter}{year_short}.pdf",
                    f"{base_new}/csi---fs-{quarter}-{year}---final.pdf",
                    f"{base_old}/csi-financial-statements-{quarter}{year_short}---final.pdf",
                    f"{base_old}/csi-fs-{quarter}-{year}.pdf",
                ])

            elif 'management discussion' in title_lower or 'md&a' in title_lower:
                possible_urls.extend([
                    f"{base_old}/csi---mda-{quarter}-{year}---final.pdf",
                    f"{base_new}/csi---mda-{quarter}-{year}---final.pdf",
                    f"{base_old}/csi-mda-{quarter}{year_short}.pdf",
                ])

        # Annual Information Form
        if 'annual information form' in title_lower:
            year_match = re.search(r'(\d{4})', title)
            if year_match:
                year = year_match.group(1)
                base = f"{self.BASE_URL}/docs/default-source/investor-relations/statutory-filings"
                possible_urls.extend([
                    f"{base}/{year}-annual-information-form---final.pdf",
                    f"{base}/csi-aif-{year}.pdf",
                ])

        return possible_urls

    def get_pdf_from_filing_page(self, filing_url: str) -> Optional[str]:
        """Scrape the actual filing page to find PDF link."""
        try:
            response = self.session.get(filing_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for PDF links
            pdf_link = soup.find('a', href=re.compile(r'\.pdf', re.IGNORECASE))
            if not pdf_link:
                pdf_link = soup.find('a', href=re.compile(r'/docs/default-source/', re.IGNORECASE))

            if pdf_link and pdf_link.get('href'):
                pdf_url = urljoin(self.BASE_URL, pdf_link['href'])
                # Clean URL - remove query params
                pdf_url = pdf_url.split('?')[0]
                return pdf_url

        except Exception as e:
            print(f"    Could not scrape page: {e}")

        return None

    def get_filings_from_page(self, page_url: str) -> List[Filing]:
        """Extract filing information from a single page."""
        try:
            response = self.session.get(page_url, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            filings = []
            seen_urls = set()

            # Find all filing links with date pattern in URL
            filing_links = soup.find_all('a', href=re.compile(r'(category/)?stat-filings/\d{4}/\d{2}/\d{2}/'))

            for link in filing_links:
                title = link.get_text(strip=True)
                href = link.get('href', '')

                # Skip if no meaningful title or already seen
                if not title or len(title) < 10 or href in seen_urls:
                    continue

                # Check if it's a main filing link (in h2, li, or has Constellation in title)
                parent = link.parent
                is_main_link = False

                if parent and parent.name in ['h2', 'li']:
                    is_main_link = True
                elif 'constellation' in title.lower():
                    is_main_link = True

                if is_main_link:
                    seen_urls.add(href)
                    filing_page_url = urljoin(self.BASE_URL, href)

                    # Extract date from URL
                    date_match = re.search(r'(\d{4})/(\d{2})/(\d{2})/', href)
                    date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}" if date_match else 'unknown'

                    # Construct possible PDF URLs
                    pdf_urls = self.construct_pdf_urls(title, date)

                    filing = Filing(
                        title=title,
                        url=filing_page_url,
                        date=date,
                        pdf_urls=pdf_urls,
                        filing_type=self._classify_filing(title),
                        year=self._extract_year(title, date),
                        quarter=self._extract_quarter(title),
                    )
                    filings.append(filing)

            return filings

        except Exception as e:
            print(f"Error parsing page {page_url}: {e}")
            return []

    def get_all_filings(self) -> List[Filing]:
        """Get all available filings from all pages."""
        all_pages = self.get_all_pages()
        all_filings = []

        for i, page_url in enumerate(all_pages, 1):
            print(f"Fetching page {i}/{len(all_pages)}...", end=" ", flush=True)

            if i > 1:
                time.sleep(1.5)

            filings = self.get_filings_from_page(page_url)
            all_filings.extend(filings)
            print(f"Found {len(filings)} filings")

        print(f"\nTotal: {len(all_filings)} filings across {len(all_pages)} pages")
        return all_filings

    def filter_filings(
        self,
        filings: List[Filing],
        year: Optional[int] = None,
        quarter: Optional[str] = None,
        filing_type: Optional[str] = None,
    ) -> List[Filing]:
        """Filter filings by year, quarter, and/or type."""
        filtered = filings

        if year:
            filtered = [f for f in filtered if f.year == year]

        if quarter:
            q = quarter.upper()
            if not q.startswith('Q'):
                q = f"Q{q}"
            filtered = [f for f in filtered if f.quarter == q]

        if filing_type:
            ft = filing_type.lower()
            filtered = [f for f in filtered if f.filing_type and ft in f.filing_type.lower()]

        return filtered

    def verify_pdf_url(self, url: str) -> bool:
        """Check if a PDF URL is valid."""
        try:
            response = self.session.head(url, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except:
            return False

    def download_filing(self, filing: Filing, verify_first: bool = True) -> bool:
        """Download a single filing."""
        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', filing.title)
        safe_title = re.sub(r'[-\s]+', '_', safe_title)[:80]
        filename = f"{filing.date}_{safe_title}.pdf"
        filepath = self.download_dir / filename

        if filepath.exists():
            print(f"  Already exists: {filename}")
            return True

        # Try constructed PDF URLs first
        for i, pdf_url in enumerate(filing.pdf_urls, 1):
            if verify_first and not self.verify_pdf_url(pdf_url):
                continue

            print(f"  Trying URL {i}/{len(filing.pdf_urls)}...")
            try:
                response = self.session.get(pdf_url, stream=True, timeout=60)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    size_mb = filepath.stat().st_size / 1024 / 1024
                    print(f"  Downloaded: {filename} ({size_mb:.1f} MB)")
                    return True
            except Exception as e:
                continue

        # Fall back to scraping the filing page
        print(f"  Scraping filing page for PDF link...")
        pdf_url = self.get_pdf_from_filing_page(filing.url)

        if pdf_url:
            try:
                response = self.session.get(pdf_url, stream=True, timeout=60)
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                size_mb = filepath.stat().st_size / 1024 / 1024
                print(f"  Downloaded: {filename} ({size_mb:.1f} MB)")
                return True
            except Exception as e:
                print(f"  Failed: {e}")

        print(f"  Could not find valid PDF link")
        return False

    def download_filings(self, filings: List[Filing]) -> int:
        """Download multiple filings. Returns count of successful downloads."""
        success = 0
        for i, filing in enumerate(filings, 1):
            print(f"\n[{i}/{len(filings)}] {filing.title}")
            if self.download_filing(filing):
                success += 1
            time.sleep(0.5)
        return success

    def create_zip(self, zip_name: str = "csi_filings.zip") -> Optional[str]:
        """Create a zip file of all downloaded PDFs."""
        pdf_files = list(self.download_dir.glob("*.pdf"))
        if not pdf_files:
            print("No files to zip!")
            return None

        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for pdf_file in pdf_files:
                zipf.write(pdf_file, pdf_file.name)

        print(f"Created zip file: {zip_name} ({len(pdf_files)} files)")
        return zip_name

    def display_filings_table(self, filings: List[Filing]):
        """Display filings in a table format."""
        if IN_COLAB:
            html = """
            <style>
                .filings-table { border-collapse: collapse; width: 100%; font-size: 14px; }
                .filings-table th { background-color: #4CAF50; color: white; padding: 12px; text-align: left; }
                .filings-table td { border: 1px solid #ddd; padding: 8px; }
                .filings-table tr:nth-child(even) { background-color: #f2f2f2; }
                .filings-table tr:hover { background-color: #ddd; }
            </style>
            <table class="filings-table">
                <tr><th>#</th><th>Date</th><th>Type</th><th>Title</th></tr>
            """
            for i, f in enumerate(filings, 1):
                html += f"<tr><td>{i}</td><td>{f.date}</td><td>{f.filing_type or ''}</td><td>{f.title}</td></tr>"
            html += "</table>"
            display(HTML(html))
        else:
            print(f"\n{'#':<4} {'Date':<12} {'Type':<20} Title")
            print("-" * 80)
            for i, f in enumerate(filings, 1):
                print(f"{i:<4} {f.date:<12} {f.filing_type or '':<20} {f.title[:40]}")


def run_interactive():
    """Run the downloader in interactive mode (for Colab/Jupyter)."""
    print("=" * 80)
    print("CSI SOFTWARE STATUTORY FILINGS DOWNLOADER")
    print("=" * 80)
    print()

    downloader = CSIFilingsDownloader()

    # Fetch all filings
    all_filings = downloader.get_all_filings()

    if not all_filings:
        print("\nNo filings found! Check your network connection.")
        return

    print("\n" + "=" * 80)
    print(f"AVAILABLE FILINGS ({len(all_filings)} total)")
    print("=" * 80)

    downloader.display_filings_table(all_filings)

    # Get unique years and types for filtering options
    years = sorted(set(f.year for f in all_filings if f.year), reverse=True)
    types = sorted(set(f.filing_type for f in all_filings if f.filing_type))

    print("\n" + "=" * 80)
    print("FILTER OPTIONS:")
    print(f"  Years available: {', '.join(map(str, years))}")
    print(f"  Types available: {', '.join(types)}")
    print("=" * 80)

    # Get year filter
    year_input = input("\nFilter by year (or Enter for all): ").strip()
    year_filter = int(year_input) if year_input.isdigit() else None

    # Get type filter
    type_input = input("Filter by type (or Enter for all): ").strip()
    type_filter = type_input if type_input else None

    # Apply filters
    filtered = downloader.filter_filings(all_filings, year=year_filter, filing_type=type_filter)

    if not filtered:
        print("\nNo filings match your filters.")
        return

    print(f"\nFiltered to {len(filtered)} filings:")
    downloader.display_filings_table(filtered)

    # Get selection
    print("\n" + "=" * 80)
    print("SELECT FILINGS TO DOWNLOAD:")
    print("  Enter numbers: 1,3,5 or 1-10 or 1,5-8,12")
    print("  Enter 'all' to download all filtered filings")
    print("=" * 80)

    selection = input("\nYour selection: ").strip()

    if not selection:
        print("No selection made.")
        return

    # Parse selection
    if selection.lower() == 'all':
        selected = filtered
    else:
        selected = []
        for part in selection.split(','):
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                for i in range(start - 1, min(end, len(filtered))):
                    if 0 <= i < len(filtered):
                        selected.append(filtered[i])
            elif part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(filtered):
                    selected.append(filtered[idx])

    if not selected:
        print("No valid filings selected.")
        return

    print(f"\nDownloading {len(selected)} filing(s)...")
    print("=" * 80)

    success = downloader.download_filings(selected)

    print("\n" + "=" * 80)
    print(f"Download complete: {success}/{len(selected)} successful")
    print("=" * 80)

    # Create zip and offer download
    pdf_files = list(downloader.download_dir.glob("*.pdf"))

    if pdf_files:
        zip_file = downloader.create_zip()

        if IN_COLAB and zip_file:
            print("\nDownloading zip file to your computer...")
            colab_files.download(zip_file)

    print("\nDone!")


# CLI support
def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(description="Download CSI Software statutory filings")
    parser.add_argument("--list", "-l", action="store_true", help="List available filings")
    parser.add_argument("--download", "-d", action="store_true", help="Download filings")
    parser.add_argument("--year", "-y", type=int, help="Filter by year")
    parser.add_argument("--quarter", "-q", type=str, help="Filter by quarter (Q1-Q4)")
    parser.add_argument("--type", "-t", type=str, help="Filter by type")
    parser.add_argument("--output", "-o", type=str, default="csi_filings", help="Output directory")
    parser.add_argument("--zip", action="store_true", help="Create zip file after download")

    args = parser.parse_args()

    if not args.list and not args.download:
        parser.print_help()
        sys.exit(1)

    downloader = CSIFilingsDownloader(download_dir=args.output)

    print("Fetching filings...")
    filings = downloader.get_all_filings()

    if not filings:
        print("No filings found.")
        sys.exit(1)

    # Apply filters
    filings = downloader.filter_filings(
        filings,
        year=args.year,
        quarter=args.quarter,
        filing_type=args.type,
    )

    if not filings:
        print("No filings match the specified filters.")
        sys.exit(1)

    if args.list:
        downloader.display_filings_table(filings)

    if args.download:
        print(f"\nDownloading {len(filings)} filings...")
        success = downloader.download_filings(filings)
        print(f"\nDownloaded {success}/{len(filings)} filings.")

        if args.zip:
            downloader.create_zip()


if __name__ == "__main__":
    # If running in notebook, use interactive mode
    if IN_COLAB or 'ipykernel' in sys.modules:
        run_interactive()
    else:
        main()
