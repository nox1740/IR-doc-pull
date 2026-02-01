# IR-doc-pull

This repository is meant to pull investor relations documents from specified websites or exchanges.

## CSI Software Statutory Filings Scraper

Scrapes and downloads statutory filings from Constellation Software Inc.'s investor relations website.

### Installation

```bash
pip install -r requirements.txt
```

### Usage

```bash
# List all available filings
python csi_stat_filings.py --list

# Download all filings
python csi_stat_filings.py --download

# Download only MD&A filings
python csi_stat_filings.py --download --type mda

# Download only 2023 filings
python csi_stat_filings.py --download --year 2023

# Download only Q4 filings
python csi_stat_filings.py --download --quarter Q4

# Download to a specific directory
python csi_stat_filings.py --download -o ./my_filings

# Combine filters
python csi_stat_filings.py --download --year 2023 --quarter Q4 --type shareholder_report

# Use known filing patterns (when live scraping is blocked)
python csi_stat_filings.py --list --use-known

# Skip URL verification (faster, useful when behind firewall)
python csi_stat_filings.py --list --use-known --no-verify
```

### Filing Types

- `shareholder_report` - Quarterly shareholder reports
- `financial_statements` - Financial statements
- `mda` - Management's Discussion and Analysis
- `aif` - Annual Information Form
- `proxy` - Proxy circulars
- `annual_report` - Annual reports

### Programmatic Usage

```python
from csi_stat_filings import CSIFilingsScraper

scraper = CSIFilingsScraper(output_dir="downloads")

# Get all filings
filings = scraper.get_filings()

# Filter filings
filtered = scraper.filter_filings(filings, year=2023, filing_type="mda")

# Download
for filing in filtered:
    scraper.download_filing(filing)
``` 
