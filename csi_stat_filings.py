#!/usr/bin/env python3
"""
CSI Software Statutory Filings Scraper

Scrapes and downloads statutory filings from Constellation Software Inc.'s
investor relations website: https://www.csisoftware.com/category/stat-filings

Usage:
    python csi_stat_filings.py --list                    # List all available filings
    python csi_stat_filings.py --download                # Download all filings
    python csi_stat_filings.py --download --type mda     # Download only MD&A filings
    python csi_stat_filings.py --download --year 2023    # Download only 2023 filings
"""

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class Filing:
    """Represents a statutory filing document."""
    title: str
    url: str
    date: Optional[str] = None
    filing_type: Optional[str] = None
    year: Optional[int] = None
    quarter: Optional[str] = None

    def __str__(self) -> str:
        parts = [self.title]
        if self.date:
            parts.append(f"({self.date})")
        return " ".join(parts)


class CSIFilingsScraper:
    """Scraper for CSI Software statutory filings."""

    BASE_URL = "https://www.csisoftware.com"
    FILINGS_URL = "https://www.csisoftware.com/category/stat-filings"

    # Common filing type patterns
    FILING_TYPES = {
        "shareholder_report": ["shareholder report", "shareholder-report"],
        "financial_statements": ["financial statements", "financial-statements"],
        "mda": ["md&a", "mda", "management's discussion"],
        "aif": ["annual information form", "aif"],
        "proxy": ["proxy", "circular"],
        "annual_report": ["annual report"],
    }

    def __init__(self, output_dir: str = "downloads"):
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

    def _get_page(self, url: str, retries: int = 3) -> Optional[str]:
        """Fetch a page with retry logic."""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                if attempt < retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Request failed, retrying in {wait_time}s... ({e})")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to fetch {url}: {e}")
                    return None
        return None

    def _classify_filing(self, title: str) -> Optional[str]:
        """Classify a filing based on its title."""
        title_lower = title.lower()
        for filing_type, patterns in self.FILING_TYPES.items():
            for pattern in patterns:
                if pattern in title_lower:
                    return filing_type
        return "other"

    def _extract_year(self, title: str, url: str) -> Optional[int]:
        """Extract the year from filing title or URL."""
        # Try to find 4-digit year in title
        year_match = re.search(r"20[0-9]{2}", title)
        if year_match:
            return int(year_match.group())

        # Try URL
        year_match = re.search(r"20[0-9]{2}", url)
        if year_match:
            return int(year_match.group())

        return None

    def _extract_quarter(self, title: str, url: str) -> Optional[str]:
        """Extract the quarter from filing title or URL."""
        text = f"{title} {url}".lower()
        quarter_match = re.search(r"q([1-4])", text)
        if quarter_match:
            return f"Q{quarter_match.group(1)}"
        return None

    def get_filings(self) -> list[Filing]:
        """Scrape all available filings from the stat filings page."""
        filings = []

        # Try to get the main page
        html = self._get_page(self.FILINGS_URL)

        if html:
            filings.extend(self._parse_filings_page(html))

        # Also check for paginated results
        page = 2
        while html:
            next_url = f"{self.FILINGS_URL}/page/{page}"
            html = self._get_page(next_url)
            if html and self._has_filings(html):
                filings.extend(self._parse_filings_page(html))
                page += 1
            else:
                break

        # If we couldn't get the page, try known filing patterns
        if not filings:
            print("Could not scrape main page, trying known filing patterns...")
            filings = self._get_known_filings()

        return filings

    def _has_filings(self, html: str) -> bool:
        """Check if the page contains any filing links."""
        soup = BeautifulSoup(html, "html.parser")
        return bool(soup.find_all("a", href=re.compile(r"\.pdf", re.I)))

    def _parse_filings_page(self, html: str) -> list[Filing]:
        """Parse filings from an HTML page."""
        filings = []
        soup = BeautifulSoup(html, "html.parser")

        # Find all PDF links
        pdf_links = soup.find_all("a", href=re.compile(r"\.pdf", re.I))

        for link in pdf_links:
            href = link.get("href", "")
            if not href:
                continue

            # Make URL absolute
            url = urljoin(self.BASE_URL, href)

            # Clean URL (remove query params that might cause issues)
            url = url.split("?")[0] if "?" in url else url

            # Get title from link text or filename
            title = link.get_text(strip=True)
            if not title:
                title = Path(urlparse(url).path).stem.replace("-", " ").replace("_", " ")

            # Extract date from surrounding elements
            date = None
            parent = link.find_parent(["li", "div", "tr", "article"])
            if parent:
                date_elem = parent.find(class_=re.compile(r"date", re.I))
                if date_elem:
                    date = date_elem.get_text(strip=True)

            filing = Filing(
                title=title,
                url=url,
                date=date,
                filing_type=self._classify_filing(title),
                year=self._extract_year(title, url),
                quarter=self._extract_quarter(title, url),
            )
            filings.append(filing)

        # Also look for article/post structures common in WordPress
        articles = soup.find_all(["article", "div"], class_=re.compile(r"post|entry|filing", re.I))
        for article in articles:
            link = article.find("a", href=re.compile(r"\.pdf", re.I))
            if link:
                continue  # Already processed above

            # Look for links to filing detail pages
            title_link = article.find("a", class_=re.compile(r"title|heading", re.I))
            if title_link:
                title = title_link.get_text(strip=True)
                detail_url = urljoin(self.BASE_URL, title_link.get("href", ""))

                # Try to get PDF from detail page
                detail_html = self._get_page(detail_url)
                if detail_html:
                    detail_soup = BeautifulSoup(detail_html, "html.parser")
                    pdf_link = detail_soup.find("a", href=re.compile(r"\.pdf", re.I))
                    if pdf_link:
                        url = urljoin(self.BASE_URL, pdf_link.get("href", ""))

                        filing = Filing(
                            title=title,
                            url=url,
                            filing_type=self._classify_filing(title),
                            year=self._extract_year(title, url),
                            quarter=self._extract_quarter(title, url),
                        )
                        filings.append(filing)

        return filings

    def _get_known_filings(self, verify: bool = True) -> list[Filing]:
        """Get filings using known URL patterns when scraping fails."""
        filings = []
        base_doc_url = "https://www.csisoftware.com/docs/default-source/investor-relations/statutory-filings"

        # Known filing patterns based on historical data
        known_patterns = [
            # Shareholder Reports
            ("Q4 2023 Shareholder Report", f"{base_doc_url}/q4-2023-shareholder-report.pdf"),
            ("Q3 2023 Shareholder Report", f"{base_doc_url}/q3-2023-shareholder-report.pdf"),
            ("Q2 2023 Shareholder Report", f"{base_doc_url}/q2-2023-shareholder-report.pdf"),
            ("Q1 2023 Shareholder Report", f"{base_doc_url}/q1-2023-shareholder-report.pdf"),
            ("Q4 2022 Shareholder Report", f"{base_doc_url}/q4-2022-shareholder-report.pdf"),
            ("Q3 2022 Shareholder Report", f"{base_doc_url}/q3-2022-shareholder-report.pdf"),
            ("Q2 2022 Shareholder Report", f"{base_doc_url}/q2-2022-shareholder-report.pdf"),
            ("Q1 2022 Shareholder Report", f"{base_doc_url}/q1-2022-shareholder-report.pdf"),
            ("Q4 2021 Shareholder Report", f"{base_doc_url}/q4-2021-shareholder-report.pdf"),
            ("Q3 2021 Shareholder Report", f"{base_doc_url}/q3-2021-shareholder-report.pdf"),
            ("Q2 2021 Shareholder Report", f"{base_doc_url}/q2-2021-shareholder-report.pdf"),
            ("Q1 2021 Shareholder Report", f"{base_doc_url}/q1-2021-shareholder-report.pdf"),
            ("Q4 2020 Shareholder Report", f"{base_doc_url}/q4-2020-shareholder-report.pdf"),
            ("Q3 2020 Shareholder Report", f"{base_doc_url}/q3-2020-shareholder-report.pdf"),
            ("Q2 2020 Shareholder Report", f"{base_doc_url}/q2-2020-shareholder-report.pdf"),
            ("Q1 2020 Shareholder Report", f"{base_doc_url}/q1-2020-shareholder-report.pdf"),
            # Financial Statements
            ("Q4 2023 Financial Statements", f"{base_doc_url}/csi-financial-statements-q423---final.pdf"),
            ("Q3 2023 Financial Statements", f"{base_doc_url}/csi-financial-statements-q323---final.pdf"),
            ("Q2 2023 Financial Statements", f"{base_doc_url}/csi-financial-statements-q223---final.pdf"),
            ("Q1 2023 Financial Statements", f"{base_doc_url}/csi-financial-statements-q123---final.pdf"),
            ("Q4 2022 Financial Statements", f"{base_doc_url}/csi-financial-statements-q422---final.pdf"),
            ("Q3 2022 Financial Statements", f"{base_doc_url}/csi-financial-statements-q322---final.pdf"),
            ("Q2 2022 Financial Statements", f"{base_doc_url}/csi-financial-statements-q222---final.pdf"),
            ("Q1 2022 Financial Statements", f"{base_doc_url}/csi-financial-statements-q122---final.pdf"),
            # MD&A
            ("Q4 2023 MD&A", f"{base_doc_url}/csi---mda-q4-2023---final.pdf"),
            ("Q3 2023 MD&A", f"{base_doc_url}/csi---mda-q3-2023---final.pdf"),
            ("Q2 2023 MD&A", f"{base_doc_url}/csi---mda-q2-2023---final.pdf"),
            ("Q1 2023 MD&A", f"{base_doc_url}/csi---mda-q1-2023---final.pdf"),
            ("Q4 2022 MD&A", f"{base_doc_url}/csi---mda-q4-2022---final.pdf"),
            ("Q3 2022 MD&A", f"{base_doc_url}/csi---mda-q3-2022---final.pdf"),
            ("Q2 2022 MD&A", f"{base_doc_url}/csi---mda-q2-2022---final.pdf"),
            ("Q1 2022 MD&A", f"{base_doc_url}/csi---mda-q1-2022---final.pdf"),
            # Annual Information Forms
            ("2023 Annual Information Form", f"{base_doc_url}/2023-annual-information-form---final.pdf"),
            ("2022 Annual Information Form", f"{base_doc_url}/2022-annual-information-form---final.pdf"),
            ("2021 Annual Information Form", f"{base_doc_url}/2021-annual-information-form---final.pdf"),
            ("2020 Annual Information Form", f"{base_doc_url}/2020-annual-information-form---final.pdf"),
            ("2019 Annual Information Form", f"{base_doc_url}/2019-annual-information-form---final.pdf"),
        ]

        for title, url in known_patterns:
            if verify:
                # Verify URL exists
                try:
                    response = self.session.head(url, timeout=10, allow_redirects=True)
                    if response.status_code != 200:
                        continue
                except requests.RequestException:
                    continue

            filing = Filing(
                title=title,
                url=url,
                filing_type=self._classify_filing(title),
                year=self._extract_year(title, url),
                quarter=self._extract_quarter(title, url),
            )
            filings.append(filing)

        return filings

    def filter_filings(
        self,
        filings: list[Filing],
        filing_type: Optional[str] = None,
        year: Optional[int] = None,
        quarter: Optional[str] = None,
    ) -> list[Filing]:
        """Filter filings by type, year, and/or quarter."""
        filtered = filings

        if filing_type:
            filing_type_lower = filing_type.lower()
            filtered = [
                f for f in filtered
                if f.filing_type and filing_type_lower in f.filing_type.lower()
            ]

        if year:
            filtered = [f for f in filtered if f.year == year]

        if quarter:
            quarter_upper = quarter.upper()
            if not quarter_upper.startswith("Q"):
                quarter_upper = f"Q{quarter_upper}"
            filtered = [f for f in filtered if f.quarter == quarter_upper]

        return filtered

    def download_filing(self, filing: Filing, overwrite: bool = False) -> Optional[Path]:
        """Download a single filing."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        filename = Path(urlparse(filing.url).path).name
        if not filename.endswith(".pdf"):
            filename = f"{filename}.pdf"

        # Clean filename
        filename = re.sub(r"[^\w\-.]", "_", filename)
        filepath = self.output_dir / filename

        if filepath.exists() and not overwrite:
            print(f"Skipping (exists): {filename}")
            return filepath

        print(f"Downloading: {filing.title}")
        print(f"  URL: {filing.url}")

        try:
            response = self.session.get(filing.url, timeout=60, stream=True)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"  Saved: {filepath}")
            return filepath

        except requests.RequestException as e:
            print(f"  Failed: {e}")
            return None

    def download_filings(
        self,
        filings: list[Filing],
        overwrite: bool = False,
    ) -> list[Path]:
        """Download multiple filings."""
        downloaded = []

        for i, filing in enumerate(filings, 1):
            print(f"\n[{i}/{len(filings)}] ", end="")
            path = self.download_filing(filing, overwrite)
            if path:
                downloaded.append(path)
            time.sleep(1)  # Be respectful to the server

        return downloaded


def main():
    parser = argparse.ArgumentParser(
        description="Scrape and download CSI Software statutory filings",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --list                     List all available filings
  %(prog)s --download                 Download all filings
  %(prog)s --download --type mda      Download only MD&A filings
  %(prog)s --download --year 2023     Download only 2023 filings
  %(prog)s --download --quarter Q4    Download only Q4 filings
  %(prog)s --download -o ./filings    Download to specific directory
        """
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available filings without downloading",
    )
    parser.add_argument(
        "--download", "-d",
        action="store_true",
        help="Download filings",
    )
    parser.add_argument(
        "--type", "-t",
        type=str,
        help="Filter by filing type (shareholder_report, financial_statements, mda, aif, proxy)",
    )
    parser.add_argument(
        "--year", "-y",
        type=int,
        help="Filter by year (e.g., 2023)",
    )
    parser.add_argument(
        "--quarter", "-q",
        type=str,
        help="Filter by quarter (Q1, Q2, Q3, Q4)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="downloads",
        help="Output directory for downloads (default: downloads)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip URL verification (use when scraping is blocked)",
    )
    parser.add_argument(
        "--use-known",
        action="store_true",
        help="Use known filing patterns instead of scraping",
    )

    args = parser.parse_args()

    if not args.list and not args.download:
        parser.print_help()
        sys.exit(1)

    scraper = CSIFilingsScraper(output_dir=args.output)

    print("Fetching available filings...")
    if args.use_known:
        print("Using known filing patterns...")
        filings = scraper._get_known_filings(verify=not args.no_verify)
    else:
        filings = scraper.get_filings()
        if not filings and args.no_verify:
            print("Falling back to known filing patterns without verification...")
            filings = scraper._get_known_filings(verify=False)

    if not filings:
        print("No filings found.")
        sys.exit(1)

    # Apply filters
    filings = scraper.filter_filings(
        filings,
        filing_type=args.type,
        year=args.year,
        quarter=args.quarter,
    )

    if not filings:
        print("No filings match the specified filters.")
        sys.exit(1)

    if args.list:
        print(f"\nFound {len(filings)} filings:\n")
        for filing in filings:
            type_str = f"[{filing.filing_type}]" if filing.filing_type else ""
            year_str = f"{filing.year}" if filing.year else ""
            quarter_str = filing.quarter or ""
            print(f"  {type_str:25} {year_str:6} {quarter_str:4} {filing.title}")
            print(f"  {'':25} URL: {filing.url}\n")

    if args.download:
        print(f"\nDownloading {len(filings)} filings to {args.output}/...")
        downloaded = scraper.download_filings(filings, overwrite=args.overwrite)
        print(f"\nDownloaded {len(downloaded)}/{len(filings)} filings successfully.")


if __name__ == "__main__":
    main()
