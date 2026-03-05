"""
Configuration file for Indeed Scrapper
Edit these settings to customize your scraping
"""

# Search Configuration
SEARCH_KEYWORDS = "software engineer"  # Job title/keywords to search
SEARCH_LOCATION = "San Francisco, CA"   # Location to search in

# Description Filtering
# Jobs will be filtered to only include those with these keywords in the description
# Set to empty list [] to disable filtering
DESCRIPTION_KEYWORDS = ["python", "react", "remote"]

# Crawling Limits
MAX_PAGES = 5      # Number of search result pages to crawl (each page has ~10-15 jobs)
MAX_JOBS = 50      # Maximum number of jobs to scrape total

# Browser Settings
HEADLESS = False   # True = browser runs in background, False = watch it work

# Output Settings
OUTPUT_FORMAT = "csv"  # Options: "csv", "json", "both"
OUTPUT_FILENAME = "indeed_jobs"

# Rate Limiting (delays in seconds)
DELAY_BETWEEN_PAGES = 2    # Delay between crawling search pages
DELAY_BETWEEN_JOBS = 1      # Delay between scraping individual jobs
