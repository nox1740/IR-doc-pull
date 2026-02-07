# IR-doc-pull
This repository is meant to pull investor relations documents from specified websites or exchanges.

## PSE EDGE Filing Scraper

A Google Colab notebook that scrapes corporate filings from the Philippine Stock Exchange EDGE portal (https://edge.pse.com.ph/) and delivers them as organized PDF files in a ZIP archive.

### Features

- **Company Search**: Search by company name or ticker symbol, select multiple companies
- **Date Range**: Filter filings by specific start and end dates
- **Filing Types**: Choose from 83 filing types (common types shown by default, rare types available via toggle)
- **Organized Output**: Files organized in `Ticker/Year/FilingType/` folder structure
- **Standardized Naming**: `Ticker_Year_Quarter_FilingType_OriginalFilename.pdf` format
- **Multi-Attachment Support**: Downloads all PDFs per disclosure, handles amendments
- **Zero-Attachment Handling**: Renders disclosure page as PDF when no attachments exist
- **Progress Logging**: Real-time status updates during download
- **Error Handling**: Continues on failure, reports all errors at end

### Usage

1. Open `PSE_EDGE_Scraper.ipynb` in Google Colab
2. Run the Setup cell to install dependencies
3. Run remaining cells to load the scraper
4. Use the interactive UI to:
   - Search and select companies
   - Set date range
   - Choose filing types
   - Click "Start Scraping"
5. Download the resulting ZIP file when complete

### Checkpoint System

The scraper includes a checkpoint system that saves progress after each file download. This allows you to resume interrupted downloads within the same Colab session.

**Important Notes:**
- Checkpoints are saved locally to `/content/checkpoints/` within the Colab session
- **Checkpoints do NOT persist after Colab timeout or disconnect**
- If the session times out (90-minute idle or 12-hour absolute limit), you will need to restart the download from scratch
- The "Resume Previous" button only works within an active session

### Requirements

See [REQUIREMENTS.md](REQUIREMENTS.md) for detailed specifications.
