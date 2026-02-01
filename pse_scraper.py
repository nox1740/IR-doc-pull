#!/usr/bin/env python3
"""
PSE EDGE Disclosure Scraper

Scrapes the Philippine Stock Exchange EDGE portal for company disclosures
and extracts PDF attachment links.

Usage:
    python pse_scraper.py
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlencode
import re
import time


class PSEEdgeScraper:
    """Scraper for PSE EDGE disclosure portal."""

    BASE_URL = "https://edge.pse.com.ph"

    # Common disclosure types on PSE EDGE
    DISCLOSURE_TYPES = {
        "Information Statement": "Information Statement",
        "Annual Report": "Annual Report",
        "Quarterly Report": "Quarterly Report",
        "Material Information": "Material Information/Transactions",
        "Press Release": "Press Release",
        "Dividend Declaration": "Declaration of Cash Dividends",
        "SEC Form 17-A": "SEC Form 17-A",
        "SEC Form 17-C": "SEC Form 17-C",
        "SEC Form 17-Q": "SEC Form 17-Q",
        "Audited Financial Statements": "Audited Financial Statements",
    }

    # Pre-populated database of major PSE-listed companies
    # Format: {symbol/alias: (cmpy_id, full_name)}
    COMPANY_DATABASE = {
        # Major conglomerates and blue chips
        "ALI": ("180", "Ayala Land, Inc."),
        "AYALA LAND": ("180", "Ayala Land, Inc."),
        "AC": ("57", "Ayala Corporation"),
        "AYALA": ("57", "Ayala Corporation"),
        "AYALA CORPORATION": ("57", "Ayala Corporation"),
        "SM": ("171", "SM Investments Corporation"),
        "SM INVESTMENTS": ("171", "SM Investments Corporation"),
        "SMPH": ("112", "SM Prime Holdings, Inc."),
        "SM PRIME": ("112", "SM Prime Holdings, Inc."),
        "BDO": ("260", "BDO Unibank, Inc."),
        "BDO UNIBANK": ("260", "BDO Unibank, Inc."),
        "JGS": ("210", "JG Summit Holdings, Inc."),
        "JG SUMMIT": ("210", "JG Summit Holdings, Inc."),
        "MER": ("118", "Manila Electric Company"),
        "MERALCO": ("118", "Manila Electric Company"),
        "MANILA ELECTRIC": ("118", "Manila Electric Company"),

        # Banks
        "BPI": ("109", "Bank of the Philippine Islands"),
        "MBT": ("79", "Metropolitan Bank & Trust Company"),
        "METROBANK": ("79", "Metropolitan Bank & Trust Company"),
        "SECB": ("197", "Security Bank Corporation"),
        "SECURITY BANK": ("197", "Security Bank Corporation"),
        "UBP": ("254", "Union Bank of the Philippines"),
        "UNIONBANK": ("254", "Union Bank of the Philippines"),
        "PNB": ("145", "Philippine National Bank"),
        "RCB": ("234", "Rizal Commercial Banking Corporation"),
        "RCBC": ("234", "Rizal Commercial Banking Corporation"),

        # Telecoms
        "TEL": ("147", "PLDT Inc."),
        "PLDT": ("147", "PLDT Inc."),
        "GLO": ("65", "Globe Telecom, Inc."),
        "GLOBE": ("65", "Globe Telecom, Inc."),
        "GLOBE TELECOM": ("65", "Globe Telecom, Inc."),

        # Property
        "MEG": ("77", "Megaworld Corporation"),
        "MEGAWORLD": ("77", "Megaworld Corporation"),
        "RLC": ("158", "Robinsons Land Corporation"),
        "ROBINSONS LAND": ("158", "Robinsons Land Corporation"),
        "FLI": ("61", "Filinvest Land, Inc."),
        "FILINVEST LAND": ("61", "Filinvest Land, Inc."),
        "VLL": ("206", "Vista Land & Lifescapes, Inc."),
        "VISTA LAND": ("206", "Vista Land & Lifescapes, Inc."),
        "DMCI": ("274", "DMCI Holdings, Inc."),

        # Food and Beverages
        "URC": ("190", "Universal Robina Corporation"),
        "UNIVERSAL ROBINA": ("190", "Universal Robina Corporation"),
        "JFC": ("93", "Jollibee Foods Corporation"),
        "JOLLIBEE": ("93", "Jollibee Foods Corporation"),
        "EMP": ("308", "Emperador Inc."),
        "EMPERADOR": ("308", "Emperador Inc."),

        # Mining and Energy
        "SCC": ("167", "Semirara Mining and Power Corporation"),
        "SEMIRARA": ("167", "Semirara Mining and Power Corporation"),
        "AP": ("185", "Aboitiz Power Corporation"),
        "ABOITIZ POWER": ("185", "Aboitiz Power Corporation"),
        "AEV": ("155", "Aboitiz Equity Ventures, Inc."),
        "ABOITIZ": ("155", "Aboitiz Equity Ventures, Inc."),
        "FGEN": ("59", "First Gen Corporation"),
        "FIRST GEN": ("59", "First Gen Corporation"),

        # Others
        "GTCAP": ("355", "GT Capital Holdings, Inc."),
        "GT CAPITAL": ("355", "GT Capital Holdings, Inc."),
        "ICT": ("328", "International Container Terminal Services, Inc."),
        "ICTSI": ("328", "International Container Terminal Services, Inc."),
        "AGI": ("268", "Alliance Global Group, Inc."),
        "ALLIANCE GLOBAL": ("268", "Alliance Global Group, Inc."),
        "PGOLD": ("317", "Puregold Price Club, Inc."),
        "PUREGOLD": ("317", "Puregold Price Club, Inc."),
        "RRHI": ("352", "Robinsons Retail Holdings, Inc."),
        "ROBINSONS RETAIL": ("352", "Robinsons Retail Holdings, Inc."),
        "WLCON": ("395", "Wilcon Depot, Inc."),
        "WILCON": ("395", "Wilcon Depot, Inc."),

        # Airlines and Transportation
        "CEB": ("302", "Cebu Air, Inc."),
        "CEBU AIR": ("302", "Cebu Air, Inc."),
        "PAL": ("137", "PAL Holdings, Inc."),
        "BLOOM": ("322", "Bloomberry Resorts Corporation"),
        "BLOOMBERRY": ("322", "Bloomberry Resorts Corporation"),

        # Cement and Construction
        "HLCM": ("211", "Holcim Philippines, Inc."),
        "HOLCIM": ("211", "Holcim Philippines, Inc."),

        # AyalaLand subsidiaries
        "AREIT": ("26", "AyalaLand Logistics Holdings Corp."),
    }

    def __init__(self):
        """Initialize the scraper with a session."""
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })
        self._companies_cache = {}

    def _get_page(self, url: str, params: dict = None) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object."""
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def _post_page(self, url: str, data: dict = None) -> Optional[BeautifulSoup]:
        """POST to a page and return BeautifulSoup object."""
        try:
            response = self.session.post(url, data=data, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            print(f"Error posting to {url}: {e}")
            return None

    def search_companies_local(self, query: str) -> list[dict]:
        """
        Search for companies in the local database.

        Args:
            query: Company name or stock symbol to search

        Returns:
            List of matching companies from local database
        """
        query_upper = query.upper().strip()
        companies = []
        seen_ids = set()

        # First try exact match
        if query_upper in self.COMPANY_DATABASE:
            cmpy_id, company_name = self.COMPANY_DATABASE[query_upper]
            companies.append({
                "cmpy_id": cmpy_id,
                "company_name": company_name,
                "stock_symbol": query_upper if len(query_upper) <= 5 else "",
            })
            seen_ids.add(cmpy_id)

        # Then try partial match
        for key, (cmpy_id, company_name) in self.COMPANY_DATABASE.items():
            if cmpy_id in seen_ids:
                continue
            if query_upper in key or query_upper in company_name.upper():
                companies.append({
                    "cmpy_id": cmpy_id,
                    "company_name": company_name,
                    "stock_symbol": key if len(key) <= 5 else "",
                })
                seen_ids.add(cmpy_id)

        return companies

    def search_companies(self, query: str) -> list[dict]:
        """
        Search for companies by name or ticker symbol.
        First checks local database, then tries online search.

        Args:
            query: Company name or stock symbol to search

        Returns:
            List of matching companies with cmpy_id and details
        """
        # First try local database (faster and works offline)
        local_results = self.search_companies_local(query)
        if local_results:
            return local_results

        # Try online search
        url = f"{self.BASE_URL}/companyDirectory/search.ax"

        data = {
            "keyword": query,
        }

        try:
            response = self.session.post(url, data=data, timeout=30)
            response.raise_for_status()

            # Parse the JSON response
            results = response.json()
            companies = []

            if isinstance(results, list):
                for item in results:
                    companies.append({
                        "cmpy_id": item.get("cmpyId"),
                        "company_name": item.get("cmpyNm"),
                        "stock_symbol": item.get("symbol"),
                    })

            return companies

        except requests.RequestException as e:
            print(f"Note: Online search failed, using local database only.")
            return []
        except ValueError:
            # Not JSON, try HTML parsing
            return self._search_companies_html(query)

    def _search_companies_html(self, query: str) -> list[dict]:
        """Fallback HTML-based company search."""
        url = f"{self.BASE_URL}/companyDirectory/form.do"
        soup = self._get_page(url)

        if not soup:
            return []

        companies = []
        query_lower = query.lower()

        # Look for company links in the directory
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "cmpy_id=" in href:
                company_name = link.get_text(strip=True)
                if query_lower in company_name.lower():
                    # Extract cmpy_id from href
                    match = re.search(r'cmpy_id=(\d+)', href)
                    if match:
                        companies.append({
                            "cmpy_id": match.group(1),
                            "company_name": company_name,
                            "stock_symbol": "",
                        })

        return companies

    def get_company_disclosures(
        self,
        cmpy_id: str,
        disclosure_type: str = "",
        start_date: str = "",
        end_date: str = "",
    ) -> list[dict]:
        """
        Get disclosures for a company with optional filters.

        Args:
            cmpy_id: Company ID from PSE EDGE
            disclosure_type: Type of disclosure to filter
            start_date: Start date in dd-mm-yyyy format
            end_date: End date in dd-mm-yyyy format

        Returns:
            List of disclosures with edge_no and details
        """
        url = f"{self.BASE_URL}/companyDisclosures/search.ax"

        # Convert date format from dd-mm-yyyy to mm/dd/yyyy (PSE format)
        formatted_start = ""
        formatted_end = ""

        if start_date:
            try:
                dt = datetime.strptime(start_date, "%d-%m-%Y")
                formatted_start = dt.strftime("%m/%d/%Y")
            except ValueError:
                print(f"Invalid start date format: {start_date}")

        if end_date:
            try:
                dt = datetime.strptime(end_date, "%d-%m-%Y")
                formatted_end = dt.strftime("%m/%d/%Y")
            except ValueError:
                print(f"Invalid end date format: {end_date}")

        data = {
            "companyId": cmpy_id,
            "keyword": disclosure_type,
            "tmplNm": disclosure_type,
            "fromDate": formatted_start,
            "toDate": formatted_end,
        }

        disclosures = []

        try:
            response = self.session.post(url, data=data, timeout=30)
            response.raise_for_status()

            results = response.json()

            if isinstance(results, dict) and "records" in results:
                for record in results["records"]:
                    disclosures.append({
                        "edge_no": record.get("edgeNo"),
                        "template_name": record.get("tmplNm"),
                        "subject": record.get("subject"),
                        "disclosure_date": record.get("disclosureDate"),
                        "company_name": record.get("cmpyNm"),
                    })
            elif isinstance(results, list):
                for record in results:
                    disclosures.append({
                        "edge_no": record.get("edgeNo"),
                        "template_name": record.get("tmplNm"),
                        "subject": record.get("subject"),
                        "disclosure_date": record.get("disclosureDate"),
                        "company_name": record.get("cmpyNm"),
                    })

        except requests.RequestException as e:
            print(f"Error fetching disclosures: {e}")
        except ValueError:
            # Try HTML parsing fallback
            disclosures = self._get_disclosures_html(cmpy_id, disclosure_type, formatted_start, formatted_end)

        return disclosures

    def _get_disclosures_html(
        self,
        cmpy_id: str,
        disclosure_type: str,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """Fallback HTML-based disclosure search."""
        url = f"{self.BASE_URL}/companyDisclosures/form.do"

        params = {"cmpy_id": cmpy_id}
        soup = self._get_page(url, params)

        if not soup:
            return []

        disclosures = []

        # Look for disclosure links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            if "openDiscViewer.do" in href or "edge_no=" in href:
                match = re.search(r'edge_no=([a-f0-9]+)', href)
                if match:
                    edge_no = match.group(1)
                    row = link.find_parent("tr")

                    template_name = ""
                    disclosure_date = ""
                    subject = link.get_text(strip=True)

                    if row:
                        cells = row.find_all("td")
                        if len(cells) >= 2:
                            template_name = cells[0].get_text(strip=True) if cells else ""
                            disclosure_date = cells[-1].get_text(strip=True) if cells else ""

                    # Apply filters if specified
                    if disclosure_type and disclosure_type.lower() not in template_name.lower():
                        continue

                    disclosures.append({
                        "edge_no": edge_no,
                        "template_name": template_name,
                        "subject": subject,
                        "disclosure_date": disclosure_date,
                        "company_name": "",
                    })

        return disclosures

    def get_disclosure_attachments(self, edge_no: str) -> list[dict]:
        """
        Get PDF attachments for a specific disclosure.

        Args:
            edge_no: The edge_no identifier for the disclosure

        Returns:
            List of attachments with file_id and download URL
        """
        url = f"{self.BASE_URL}/openDiscViewer.do"
        params = {"edge_no": edge_no}

        soup = self._get_page(url, params)

        if not soup:
            return []

        attachments = []

        # Look for download links
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")

            # Match downloadFile.do links
            if "downloadFile.do" in href:
                match = re.search(r'file_id=(\d+)', href)
                if match:
                    file_id = match.group(1)
                    filename = link.get_text(strip=True)

                    # Clean up filename
                    if not filename:
                        filename = f"attachment_{file_id}.pdf"

                    download_url = urljoin(self.BASE_URL, href)

                    attachments.append({
                        "file_id": file_id,
                        "filename": filename,
                        "download_url": download_url,
                    })

            # Also check for downloadHtml.do (HTML disclosures that may have PDFs)
            elif "downloadHtml.do" in href:
                match = re.search(r'edge_no=([a-f0-9]+)', href)
                if match:
                    filename = link.get_text(strip=True) or "main_document.html"
                    download_url = urljoin(self.BASE_URL, href)

                    attachments.append({
                        "file_id": None,
                        "filename": filename,
                        "download_url": download_url,
                    })

        # Also look for attachment lists in tables
        attachment_table = soup.find("table", {"id": "attachments"}) or soup.find("div", {"class": "attachments"})
        if attachment_table:
            for link in attachment_table.find_all("a", href=True):
                href = link.get("href", "")
                if "file_id=" in href:
                    match = re.search(r'file_id=(\d+)', href)
                    if match:
                        file_id = match.group(1)
                        # Avoid duplicates
                        if not any(a["file_id"] == file_id for a in attachments):
                            filename = link.get_text(strip=True) or f"attachment_{file_id}.pdf"
                            download_url = urljoin(self.BASE_URL, href)

                            attachments.append({
                                "file_id": file_id,
                                "filename": filename,
                                "download_url": download_url,
                            })

        return attachments

    def download_file(self, file_id: str, output_path: str) -> bool:
        """
        Download a file by its file_id.

        Args:
            file_id: The file ID from PSE EDGE
            output_path: Path to save the downloaded file

        Returns:
            True if download succeeded, False otherwise
        """
        url = f"{self.BASE_URL}/downloadFile.do"
        params = {"file_id": file_id}

        try:
            response = self.session.get(url, params=params, timeout=60, stream=True)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            return True

        except requests.RequestException as e:
            print(f"Error downloading file {file_id}: {e}")
            return False

    def list_companies(self) -> list[dict]:
        """
        List all companies in the local database.

        Returns:
            List of all companies with their symbols and IDs
        """
        seen_ids = set()
        companies = []

        for key, (cmpy_id, company_name) in self.COMPANY_DATABASE.items():
            if cmpy_id not in seen_ids:
                # Find the symbol (shortest key for this company)
                symbol = ""
                for k, (cid, _) in self.COMPANY_DATABASE.items():
                    if cid == cmpy_id and len(k) <= 5:
                        if not symbol or len(k) < len(symbol):
                            symbol = k

                companies.append({
                    "cmpy_id": cmpy_id,
                    "company_name": company_name,
                    "stock_symbol": symbol,
                })
                seen_ids.add(cmpy_id)

        # Sort by company name
        companies.sort(key=lambda x: x["company_name"])
        return companies

    def get_disclosure_url(self, cmpy_id: str) -> str:
        """
        Get the URL for viewing company disclosures.

        Args:
            cmpy_id: The company ID

        Returns:
            URL to the company's disclosure page
        """
        return f"{self.BASE_URL}/companyDisclosures/form.do?cmpy_id={cmpy_id}"

    def get_download_url(self, file_id: str) -> str:
        """
        Get the download URL for a file.

        Args:
            file_id: The file ID

        Returns:
            Direct download URL
        """
        return f"{self.BASE_URL}/downloadFile.do?file_id={file_id}"


def format_date_input(date_str: str) -> str:
    """Validate and format date input."""
    try:
        datetime.strptime(date_str, "%d-%m-%Y")
        return date_str
    except ValueError:
        return ""


def print_available_companies(scraper: PSEEdgeScraper):
    """Print list of available companies in the database."""
    print("\nAvailable companies in the local database:")
    print("-" * 60)
    companies = scraper.list_companies()
    for company in companies:
        print(f"  {company['stock_symbol']:6} - {company['company_name']}")
    print("-" * 60)
    print(f"Total: {len(companies)} companies")


def main():
    """Main CLI interface for the PSE EDGE scraper."""
    print("=" * 60)
    print("PSE EDGE Disclosure Scraper")
    print("=" * 60)
    print()

    scraper = PSEEdgeScraper()

    # Get user inputs
    company_query = input("Enter company name or ticker (e.g., Ayala Land, ALI) [or 'list' to see all]: ").strip()

    if company_query.lower() == "list":
        print_available_companies(scraper)
        company_query = input("\nEnter company name or ticker: ").strip()

    if not company_query:
        print("Error: Company name is required.")
        return

    disclosure_type = input("Enter disclosure type (e.g., Information Statement): ").strip()

    start_date = input("Enter start date (dd-mm-yyyy, e.g., 01-01-2025): ").strip()
    start_date = format_date_input(start_date)

    end_date = input("Enter end date (dd-mm-yyyy, e.g., 31-12-2025): ").strip()
    end_date = format_date_input(end_date)

    print()
    print("-" * 60)
    print(f"Searching for company: {company_query}")
    print("-" * 60)

    # Search for the company
    companies = scraper.search_companies(company_query)

    if not companies:
        print("\nNo companies found matching your query in local database.")
        print("Trying online search...")

        # Try HTML parsing fallback
        companies = scraper._search_companies_html(company_query)

    if not companies:
        print("Could not find any matching companies.")
        print("\nTip: Type 'list' to see all available companies in the local database.")
        print("     Or visit: https://edge.pse.com.ph/companyDirectory/form.do")
        return

    # Display found companies
    print(f"\nFound {len(companies)} company(ies):")
    for i, company in enumerate(companies, 1):
        symbol = company.get("stock_symbol", "")
        symbol_display = f" ({symbol})" if symbol else ""
        print(f"  {i}. {company['company_name']}{symbol_display} - ID: {company['cmpy_id']}")

    # Select company
    if len(companies) > 1:
        selection = input("\nSelect company number (default: 1): ").strip()
        try:
            idx = int(selection) - 1 if selection else 0
            if idx < 0 or idx >= len(companies):
                idx = 0
        except ValueError:
            idx = 0
    else:
        idx = 0

    selected_company = companies[idx]
    cmpy_id = selected_company["cmpy_id"]

    print()
    print("-" * 60)
    print(f"Searching disclosures for: {selected_company['company_name']}")
    if disclosure_type:
        print(f"Disclosure type: {disclosure_type}")
    if start_date:
        print(f"Date range: {start_date} to {end_date or 'present'}")
    print("-" * 60)

    # Get disclosures
    disclosures = scraper.get_company_disclosures(
        cmpy_id=cmpy_id,
        disclosure_type=disclosure_type,
        start_date=start_date,
        end_date=end_date,
    )

    if not disclosures:
        print("\nNo disclosures found matching your criteria.")
        print("\nThis could mean:")
        print("  1. No disclosures match your search criteria")
        print("  2. The PSE EDGE website is not accessible from your network")
        print()
        print("You can try accessing the disclosures directly at:")
        print(f"  {scraper.get_disclosure_url(cmpy_id)}")
        print()
        print("Common disclosure types to search for:")
        for key in scraper.DISCLOSURE_TYPES:
            print(f"  - {key}")
        return

    print(f"\nFound {len(disclosures)} disclosure(s):")
    print()

    all_pdfs = []

    for i, disclosure in enumerate(disclosures, 1):
        print(f"{i}. [{disclosure.get('template_name', 'N/A')}]")
        print(f"   Subject: {disclosure.get('subject', 'N/A')}")
        print(f"   Date: {disclosure.get('disclosure_date', 'N/A')}")
        print(f"   Edge No: {disclosure.get('edge_no', 'N/A')}")

        # Get attachments for this disclosure
        edge_no = disclosure.get("edge_no")
        if edge_no:
            viewer_url = f"{scraper.BASE_URL}/openDiscViewer.do?edge_no={edge_no}"
            print(f"   View: {viewer_url}")

            print("   Fetching attachments...")
            attachments = scraper.get_disclosure_attachments(edge_no)

            if attachments:
                print(f"   PDF Attachments ({len(attachments)}):")
                for att in attachments:
                    print(f"      - {att['filename']}")
                    print(f"        URL: {att['download_url']}")
                    all_pdfs.append({
                        "disclosure_subject": disclosure.get("subject"),
                        "disclosure_date": disclosure.get("disclosure_date"),
                        **att,
                    })
            else:
                print("   No PDF attachments found.")

        print()
        time.sleep(0.5)  # Be respectful to the server

    # Summary
    print("=" * 60)
    print("SUMMARY: Available PDF Files")
    print("=" * 60)

    if all_pdfs:
        print(f"\nTotal PDF files found: {len(all_pdfs)}\n")
        for i, pdf in enumerate(all_pdfs, 1):
            print(f"{i}. {pdf['filename']}")
            print(f"   Disclosure: {pdf.get('disclosure_subject', 'N/A')}")
            print(f"   Date: {pdf.get('disclosure_date', 'N/A')}")
            print(f"   Download URL: {pdf['download_url']}")
            print()
    else:
        print("\nNo PDF files found for the specified criteria.")

    return all_pdfs


if __name__ == "__main__":
    main()
