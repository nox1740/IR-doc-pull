# PSE EDGE Filing Scraper - Requirements

## Overview

This document specifies requirements for a web-based scraper that pulls corporate filings from the Philippine Stock Exchange EDGE portal (https://edge.pse.com.ph/) and delivers them as organized PDF files in a ZIP archive.

---

## 1. Platform & Deployment

**PLATFORM:** Google Colab notebook
- Browser-based access (works on iPad, desktop, iPhone, Android)
- Zero installation required
- User grants Google Drive mount permission once on first run

**SESSION MANAGEMENT:**
- Colab has 90-minute idle timeout and 12-hour absolute limit
- Checkpoint/resume system saves progress to Google Drive after each file
- On timeout/interruption, user can resume from last successful download
- Checkpoint file stores: batch parameters, downloaded files list, current position

---

## 2. User Interface

**FORM LAYOUT:**
- Company search box (live search, accepts company names OR ticker symbols)
- Date range picker (specific start/end dates, not just years)
- Filing type checkboxes (see Section 10 for complete list)
  - Rare types (filed <1x/year) hidden by default
  - "Show all" toggle reveals all 83 types
- Submit button
- Download button (appears when complete)

**RESPONSIVE DESIGN:**
- Single column on phones
- Wider layout on tablets/desktop

**PROGRESS DISPLAY:**
- Real-time log updating per file downloaded
- Format: `[timestamp] [status] Ticker — FilingType — Date — Filename`
- Status indicators: ✓ (success), ⚠ (rendered from page), errors in final summary

---

## 3. Input Parameters

**COMPANIES:**
- Multiple companies per request (no limit)
- Input via company name OR ticker symbol
- Live search shows both names and tickers

**DATE RANGE:**
- Specific calendar dates (start and end)
- No limit on range width
- Multiple years supported

**FILING TYPES:**
- Multiple types per request (no limit)
- 83 filing types total (see Section 10)
- Shortened names used throughout (e.g., "QuarterlyRpt" not "Quarterly Report")

---

## 4. Scraping Method

**DATA SOURCE:**
- URL: https://edge.pse.com.ph/
- Public access (no authentication)
- PDFs already hosted on PSE EDGE

**TECHNICAL APPROACH:**
- Use backend API (GitHub project bldulam1/pse-edge) for disclosure listings
- Parse HTML from openDiscViewer.do pages for attachment details
- Download all PDF attachments per disclosure
- Render zero-attachment filings as PDFs (page with metadata)

**PAGINATION:**
- Page-by-page navigation through disclosure listings
- No "show all" option available on PSE EDGE

---

## 5. File Naming Convention

**STANDARD FORMAT:**
```
Ticker_Year_Quarter_FilingType_OriginalFilename.pdf
```

**COMPONENTS:**
- **Ticker:** Company stock symbol (e.g., JFC, RRHI)
- **Year:** Disclosure date year (YYYY)
- **Quarter:** Only for quarterly filings (Q1, Q2, Q3, Q4)
- **FilingType:** Shortened name (e.g., QuarterlyRpt, AnnualRpt)
- **OriginalFilename:** Appended only when multiple PDFs exist

**QUARTER DERIVATION - TWO METHODS:**

**Method 1 - Backward** (for Quarterly Report 17-2 and Disbursement 4-29):
- Filed Jan-Mar = Q4 of prior year
- Filed Apr-Jun = Q1
- Filed Jul-Sep = Q2
- Filed Oct-Dec = Q3

**Method 2 - Forward/Calendar** (for POR-1, POR-2, 17-12):
- Filed Jan-Mar = Q1
- Filed Apr-Jun = Q2
- Filed Jul-Sep = Q3
- Filed Oct-Dec = Q4

**QUARTER EXTRACTION:**
- Primary: Parse from PDF filename (patterns: Q1, Q2, 17-Q3, (Q3 2024), Q1 2024)
- Fallback: Derive from disclosure date using rules above
- Omit quarter entirely for non-quarterly filings

**FILENAME SANITIZATION:**
- Replace spaces with underscores
- Remove special characters (`/\:*?"<>|`)
- Strip redundant ticker/year/quarter from appended original filename
- Append original filename ONLY when multiple PDFs exist

**COLLISION HANDLING:**
- Add disclosure date (YYYYMMDD) if duplicate
- Add sequential number (_1, _2, _3) if still duplicate

**ZERO-ATTACHMENT FILINGS:**
- Use disclosure date in place of missing original filename
- Format: `Ticker_Year_Quarter_FilingType_YYYYMMDD.pdf`

---

## 6. Folder Structure

**HIERARCHY:**
```
Ticker/Year/FilingType/
```

**EXAMPLE:**
```
JFC/
  2023/
    QuarterlyRpt/
      JFC_2023_Q1_QuarterlyRpt_MainReport.pdf
      JFC_2023_Q1_QuarterlyRpt_ConsolidatedFS.pdf
      JFC_2023_Q2_QuarterlyRpt_20230715.pdf
    DisburseRpt/
      JFC_2023_Q2_DisburseRpt_ProgressReport.pdf
  2024/
    AnnualRpt/
      JFC_2024_AnnualRpt_17A.pdf
```

**NOTES:**
- Ticker used in folder names (not full company name)
- Year is disclosure date year
- All PDFs from same filing type/year/ticker in same folder
- No sub-folders per individual disclosure

---

## 7. Output Files

**SINGLE VS. MULTIPLE:**
- Single filing (1 total): PDF download
- Multiple filings (2+): ZIP download

**ZIP ASSEMBLY:**
- All files held in memory during processing
- ZIP assembled at end
- Automatic download when complete

**SIZE WARNING:**
- Display if ZIP exceeds 100MB
- Show warning AFTER assembly, BEFORE download
- Allow download to proceed regardless

---

## 8. Multi-Attachment Handling

**ATTACHMENT SCOPE:**
- Download ALL PDF attachments for each disclosure
- Includes "Main Document" section AND "Attachments" section

**AMENDMENTS:**
- When multiple versions exist ([Amend-2], [Amend-1], original):
  - Pull ONLY latest amendment from Main Document section
  - Pull all items from Attachments section

**ZERO-ATTACHMENT FILINGS:**
- Some filings have no PDFs and no download button
- Render disclosure viewer page as PDF
- Include: company name, disclosure date, template name, "Attachments (0)"
- Maintain PSE EDGE page styling (logo, layout)

**MULTIPLE PDFs PER FILING:**
- Each attachment gets separate file
- Append sanitized original filename to base name
- Example with 3 attachments:
  - `APOLLO_2024_AnnualRpt_17A-Report.pdf`
  - `APOLLO_2024_AnnualRpt_Consolidated-AFS.pdf`
  - `APOLLO_2024_AnnualRpt_Separate-AFS.pdf`

---

## 9. Error Handling

**STRATEGY:**
- Skip failed filing, continue processing rest
- No mid-process stops
- Report all errors at end

**ERROR TYPES TO TRACK:**
- No results found
- Network timeout
- PSE EDGE blocking
- PDF download failure

**ERROR SUMMARY FORMAT** (displayed as text on screen):
- Total error count
- List of failed filings showing:
  - Company ticker
  - Filing type
  - Disclosure date
  - Error type/reason

**SPECIAL CASES:**
- PSE EDGE downtime: No upfront check, failures reported at end
- Zero-attachment filings: NOT errors, handle silently

---

## 10. Filing Type Master List (83 Types)

### Common Filings
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 17-1 | AnnualRpt | Annual Report |
| 17-2 | QuarterlyRpt | Quarterly Report |
| 4-29 | DisburseRpt | Disbursement of Proceeds and Progress Report |
| 4-30 | MatInfo | Material Information/Transactions |
| 4-31 | PressRel | Press Release |
| 6-1 | CashDiv | Declaration of Cash Dividends |
| 6-2 | StockDiv | Declaration of Stock Dividends |

### Corporate Actions
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 4-1 | AcqDisp-Assets | Acquisition or Disposition of Assets |
| 4-2 | AcqDisp-Shares | Acquisition or Disposition of Shares |
| 4-3 | Amend-AOI | Amendments to Articles of Incorporation |
| 4-4 | Amend-BL | Amendments to By-Laws |
| 4-5 | ChgControl | Change in Control of Issuer |
| 4-8 | ChgDirOff | Change in Directors and/or Officers |
| 4-23 | MergerCons | Mergers and Consolidations |
| 5-1 | SubAcq | Substantial Acquisitions |

### Meetings & Governance
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 4-24 | ASM-Results | Results of Annual/Special Stockholders' Meeting |
| 4-25 | BOD-Results | Results of Organizational Meeting of BOD |
| 7-1 | ASM-Notice | Notice of Annual/Special Stockholders' Meeting |
| 7-2 | ASM-Postpone | Postponement of Annual Stockholders' Meeting |
| I-ACGR | CorpGov | Integrated Annual Corporate Governance Report |

### Ownership & Securities
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 17-6 | InitBenOwn | Initial Statement of Beneficial Ownership |
| 17-7 | ChgBenOwn | Statement of Changes in Beneficial Ownership |
| 17-8 | Own5Pct | Report by Owner of More Than Five Percent |
| 17-11 | StockholdersLst | List of Stockholders |
| 17-12 | Top100Stockholders | List of Top 100 Stockholders |
| 17-13 | ForeignOwn | Foreign Ownership Report |
| POR-1 | PubOwn | Public Ownership Report |
| POR-2 | PubOwnClass | Public Ownership Report (Classified Shares) |

### Securities Issuance
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 4-14 | RightsOffer | Stock Rights Offering |
| 4-15 | NewEquity | Creation and Issuance of New Equity Security |
| 4-16 | DebtIssue | Issuance of Debt Securities |
| 4-17 | Warrants | Issuance of Warrants |
| 4-18 | Options | Options |

### Share Transactions
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 9-1 | BuyBack | Share Buy-Back Transactions |
| 9-2 | TreasurySale | Sale of Treasury Shares |
| 4-11 | ChgShares | Change in Number of Issued/Outstanding Shares |
| 4-19 | Declassify | Declassification of Shares |
| 4-20 | Reclassify | Reclassification of Shares |
| 4-21 | Redemption | Redemption of Security |

### Change Notifications
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 4-6 | ChgContact | Change in Corporate Contact Details/Website |
| 4-7 | ChgName | Change in Corporate Name/Stock Symbol |
| 4-9 | ChgAuditor | Change in External Auditor |
| 4-10 | ChgFiscalYr | Change in Fiscal Year |
| 4-12 | ChgParVal | Change in Par Value |
| 12-1 | ChgSTA | Change in Stock Transfer Agent |
| 13-1 | ChgDirHoldings | Change in Shareholdings of Directors/Officers |

### Communications
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 4-13 | ClarNews | Clarification of News Reports |
| 4-32 | ExchReply | Reply to Exchange's Query |
| 14-1 | InvBriefing | Notice of Analysts'/Investors' Briefing |
| 16-1 | CorpUpdate | Update on Corporate Actions/Transactions |

### Trading
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 4-33 | VolHalt | Voluntary Trading Halt |
| 4-34 | VolSuspend | Voluntary Trading Suspension |
| CMIC-2 | UPM-Reply | Reply to Inquiry on Unusual Price Movement |

### Legal & Regulatory
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 4-26 | LegalProc | Legal Proceedings |
| 4-27 | OfferComp | Notification of Completion/Termination of Offering |
| 4-28 | AuditFindings | Findings of External Auditor (Fraud and Error) |
| 17-16 | TenderOffer | Tender Offer Report |

### Other Categories
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 6-3 | PropDiv | Declaration of Property Dividends |
| 10-1 | SubAcqDisp | Acquisition/Disposition by Subsidiaries/Affiliates |
| 11-1 | VolLockUp | Voluntary Lock-Up |
| BL-1 | BackdoorList | Comprehensive Disclosure on Backdoor Listing |
| LR-1 | ShareIssuance | Comprehensive Disclosure on Issuance of Shares |
| LR-2 | PlaceSub | Comprehensive Disclosure on Placing/Subscription |
| LR-3 | ListingApp | Submission of Documents for Listing Applications |
| DLR-1 | VolDelist | Voluntary Delisting |
| DLR-2 | DelistPetition | Petition for Voluntary Delisting |
| QR-1 | QuasiReorg | Quasi-Reorganization |
| 4-22 | JointVenture | Joint Ventures |

### Reporting Extensions & Other
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| 17-3 | ExtReq-17A | Request for Extension to File SEC Form 17-A |
| 17-4 | ExtReq-17Q | Request for Extension to File SEC Form 17-Q |
| 17-5 | InfoStatement | Information Statement |
| 17-9 | InstOwn5Pct | Short Form Report by Institutional Owners |
| 17-10 | NumShareholders | Report on the Number of Shareholders |
| 17-14 | MGB-Verify | Annual Verification of Mines and Geosciences Bureau |
| 17-15 | DOE-Verify | Annual Verification of Department of Energy |
| 17-18 | OtherSEC | Other SEC Forms, Reports and Requirements |
| CP-TR1 | CPTechRpt | CP Technical Report |

### ETF Forms (Rare - Hidden by Default)
| Form No. | Short Name | Full Name |
|----------|------------|-----------|
| ETF-1 | ETF-DailyTrade | Daily Trading Information |
| ETF-2 | ETF-MonthlyRpt | Monthly Issuance and Redemption Report |
| ETF-3 | ETF-Dividend | Dividend Distribution |
| ETF-4 | ETF-CreateShares | Creation of Shares |
| ETF-5 | ETF-RedeemShares | Redemption of Shares |
| ETF-6 | ETF-ChgAuthPart | Change in Authorized Participant |
| ETF-7 | ETF-ChgCustodian | Change in Custodian |
| ETF-8 | ETF-ChgFundMgr | Change in Fund Manager |
| ETF-9 | ETF-ChgIdxProv | Change in Index Provider |
| ETF-10 | ETF-ChgMktMkr | Change in Market Maker |
| ETF-11 | ETF-ChgTA | Change in Transfer Agent |
| ETF-12 | ETF-MatInfo | Material Information |

### Quarterly Filings (include quarter in filename)
- **17-2 (QuarterlyRpt)** - backward derivation
- **4-29 (DisburseRpt)** - backward derivation
- **POR-1 (PubOwn)** - forward derivation
- **POR-2 (PubOwnClass)** - forward derivation
- **17-12 (Top100Stockholders)** - forward derivation

---

## 11. Technical Notes

**DEPENDENCIES:**
- Entirely free (no paid services)
- Self-contained in Colab notebook
- User installs nothing locally

**PSE EDGE STRUCTURE:**
- Disclosure listings: JavaScript-loaded (use backend API)
- Filing viewer pages: Static HTML (parse directly)
- Download links: JavaScript anchors (construct URLs from metadata)
- Backend API: Use bldulam1/pse-edge GitHub wrapper

**RECOMMENDED WORKFLOW:**
1. Get company list via backend API
2. Search disclosures by company/date/type via API
3. Navigate paginated results via API
4. For each disclosure:
   - Fetch viewer page HTML
   - Parse attachment details
   - Identify latest amendment if multiple versions
   - Download all PDFs OR render page if zero attachments
   - Log progress
   - Save checkpoint
5. Assemble ZIP in memory
6. Display error summary
7. Trigger download

**CHECKPOINT FILE CONTENTS:**
- Batch parameters (companies, dates, filing types)
- List of successfully downloaded files
- Current position in disclosure listings
- Next disclosure to process

**RESUME LOGIC:**
- Load checkpoint on session restart
- Skip already-downloaded files
- Continue from next unprocessed disclosure

---

## 12. Out of Scope

**NOT INCLUDED:**
- User accounts or authentication
- Data persistence or caching
- Historical archive of scrapes
- Scheduled/automated pulls
- Email notifications
- Share/export beyond ZIP download
- PDF editing or annotation
- Content comparison or analytics
- External system integration
- Programmatic API access
- Auto-update of filing type list (manual only)

---

## Project Info

- **Platform:** Google Colab
- **Total Filing Types:** 83
- **Created For:** Allan
- **Project:** PSE EDGE Filing Scraper
