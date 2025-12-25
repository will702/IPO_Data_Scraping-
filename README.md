# IPO Data Scraper

A Python web scraper that extracts IPO (Initial Public Offering) data from [e-IPO.co.id](https://e-ipo.co.id), Indonesia's electronic IPO platform. The scraper collects comprehensive IPO information including company details, ticker symbols, listing dates, pricing information, and more.

## Features

- **Comprehensive Data Extraction**: Scrapes multiple data points for each IPO including:

  - Company name and ticker symbol
  - IPO status (Pre-Effective, Book Building, Offering, Closed, etc.)
  - Sector classification
  - Sharia compliance indicator
  - Listing date
  - Book building period and price range
  - Final offering price
  - Shares offered (in lots)
  - Detail page URL

- **Pagination Support**: Automatically handles paginated results across multiple pages
- **Deduplication**: Removes duplicate entries within and across pages
- **Multiple Output Formats**: Exports data to both CSV and JSON formats
- **Rate Limiting**: Includes configurable delays between requests to be respectful to the server

## Requirements

- Python 3.7+
- `requests` - HTTP library for making web requests
- `beautifulsoup4` - HTML parsing library

## Installation

1. Install the required dependencies:

```bash
pip install requests beautifulsoup4
```

Or using a requirements file:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

The script can be imported and used programmatically:

```python
from IPO_Data_Scraper import scrape_all, write_csv, write_json

# Scrape all IPO data (defaults to max 200 pages, 0.7s delay)
items = scrape_all()

# Export to CSV
write_csv("ipo_data.csv", items)

# Export to JSON
write_json("ipo_data.json", items)
```

### Custom Configuration

```python
# Scrape with custom settings
items = scrape_all(
    max_pages=100,      # Maximum number of pages to scrape
    sleep_s=1.0         # Delay between requests in seconds
)
```

### Command Line Usage

The script includes a test mode that can be run directly:

```bash
python IPO_Data_Scraper.py
```

This will test fetching the first page and print the HTML length.

## Data Structure

Each IPO item contains the following fields:

| Field                      | Type        | Description                                                       |
| -------------------------- | ----------- | ----------------------------------------------------------------- |
| `company_name`             | str         | Full company name (e.g., "PT Super Bank Indonesia Tbk")           |
| `ticker`                   | str \| None | Stock ticker symbol (e.g., "SUPA")                                |
| `status`                   | str \| None | IPO status (Pre-Effective, Book Building, Offering, Closed, etc.) |
| `sector`                   | str \| None | Industry sector                                                   |
| `sharia`                   | bool        | Whether the IPO is Sharia-compliant                               |
| `listing_date`             | str \| None | Listing date in "DD MMM YYYY" format                              |
| `bookbuilding_period`      | str \| None | Book building period (e.g., "09 Dec 2020 - 17 Dec 2020")          |
| `final_price`              | str \| None | Final offering price (e.g., "Rp 635")                             |
| `bookbuilding_price_range` | str \| None | Book building price range (e.g., "Rp 298 - Rp 328")               |
| `shares_offered_lot`       | str \| None | Number of shares offered in lots (e.g., "44.066.123 Lot")         |
| `detail_url`               | str \| None | URL to the detailed IPO page                                      |

## Output Files

- **CSV Format**: `eipo_ipo_list.csv` - Tabular data suitable for spreadsheet applications
- **JSON Format**: `eipo_ipo_list.json` - Structured data with UTF-8 encoding and pretty formatting

## Technical Details

### Scraping Strategy

- Uses the list view endpoint: `https://e-ipo.co.id/id/ipo/index?page=N&per-page=12&view=list`
- Parses HTML using BeautifulSoup
- Extracts data from card-based layouts
- Handles Indonesian language labels and formatting

### Error Handling

- Automatically stops when pagination runs out (no more items found)
- Includes session warmup to establish cookies
- Handles 403 errors with helpful error messages

### Known Limitations

- The site may implement anti-scraping measures (WAF, JavaScript requirements)
- If you encounter 403 errors, consider using a browser automation tool like Playwright
- Some fields may be `None` if not available for a particular IPO

## Example Output

```json
[
  {
    "company_name": "PT Super Bank Indonesia Tbk",
    "ticker": "SUPA",
    "status": "Closed",
    "sector": "Financials",
    "sharia": false,
    "listing_date": "17 Dec 2025",
    "bookbuilding_period": "09 Dec 2020 - 17 Dec 2020",
    "final_price": "Rp 635",
    "bookbuilding_price_range": "Rp 298 - Rp 328",
    "shares_offered_lot": "44.066.123 Lot",
    "detail_url": "https://e-ipo.co.id/id/ipo/detail/..."
  }
]
```

## License

This script is provided as-is for educational and research purposes. Please respect the website's terms of service and robots.txt when using this scraper.

## Notes

- The scraper includes rate limiting to avoid overwhelming the server
- Data is extracted from the public list view pages
- Some IPO statuses may vary (Pre-Effective, Book Building, Waiting For Offering, Offering, Allotment, Closed, Postpone, Canceled)
