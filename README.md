# Indeed Scrapper & Crawler

A combined web crawler and scraper for extracting job listings from Indeed.com with a Web UI.

## Quick Start (Web UI)

The easiest way to use this scrapper is with the built-in web interface:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web server
python app.py
```

Then open your browser to: **http://127.0.0.1:5000**

The web UI lets you:
- Configure search parameters visually
- Watch the scraping progress in real-time
- View results in a sortable table
- Export to CSV or JSON with one click

## Features

### Web UI
- Beautiful, responsive interface
- Real-time progress tracking
- Live status updates
- One-click export to CSV/JSON
- Configure all options without editing code

### Crawler Component
- Discovers job URLs across multiple search result pages
- Follows pagination automatically
- Manages URL queue to avoid duplicates
- Configurable search keywords and locations

### Scraper Component
- Extracts structured data from job postings:
  - Job Title
  - Company Name
  - Company Domain (auto-generated)
  - Job Location
  - Description (with keyword filtering)
  - Job Post URL
  - Date Posted
  - Employment Type (full-time, contract, etc.)
  - Salary
  - Status (active/closed)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Option 1: Edit config.py

1. Edit `config.py` with your settings:
```python
SEARCH_KEYWORDS = "python developer"
SEARCH_LOCATION = "Remote"
DESCRIPTION_KEYWORDS = ["django", "fastapi"]
MAX_PAGES = 10
MAX_JOBS = 100
```

2. Run the scraper:
```bash
python indeed_scrapper.py
```

### Option 2: Use as a module

```python
from indeed_scrapper import IndeedCrawlerScraper

scraper = IndeedCrawlerScraper(
    search_keywords="data scientist",
    search_location="New York, NY",
    description_keywords=["python", "sql", "machine learning"],
    max_pages=5,
    max_jobs=50,
    headless=False
)

scraper.run(output_format="csv")
```

## Output Files

- `indeed_jobs.csv` - Job data in CSV format
- `indeed_jobs.json` - Job data in JSON format (if enabled)

## Configuration Options

| Setting | Description |
|---------|-------------|
| `SEARCH_KEYWORDS` | Job title/keywords to search |
| `SEARCH_LOCATION` | Location (city, state, or "Remote") |
| `DESCRIPTION_KEYWORDS` | Filter jobs by description keywords |
| `MAX_PAGES` | Number of search pages to crawl |
| `MAX_JOBS` | Maximum jobs to scrape |
| `HEADLESS` | Run browser in background (True/False) |
| `OUTPUT_FORMAT` | "csv", "json", or "both" |

## Notes

- The scraper uses Selenium to handle JavaScript-rendered content
- Delays are built in to avoid being blocked
- Company domains are auto-generated from company names
- Status is marked "active" if the job page is accessible
# TrovoLavoro-Job-Scraper
