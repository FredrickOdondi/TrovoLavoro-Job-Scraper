"""
TrovoLavoro Scrapper & Crawler
Italian job site scraper with full data extraction
"""

import time
import re
import os
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup


class TrovoLavoroScraper:
    """
    Crawler + Scraper for TrovoLavoro Italian job site
    """

    BASE_URL = "https://offerte-di-lavoro.trovolavoro.com"

    def __init__(
        self,
        search_keywords: str = "",
        max_pages: int = 10,
        max_jobs: int = 100,
        headless: bool = True
    ):
        self.search_keywords = search_keywords.lower() if search_keywords else ""
        self.max_pages = max_pages
        self.max_jobs = max_jobs
        self.headless = headless

        self.scraped_jobs: List[Dict] = []
        self.driver = None

    def _setup_driver(self):
        """Setup Chrome driver with Brave browser"""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        brave_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        if os.path.exists(brave_path):
            options.binary_location = brave_path

        driver_path = os.path.expanduser("~/chromedriver145")
        if os.path.exists(driver_path):
            print(f"Using ChromeDriver 145: {driver_path}")
            self.driver = webdriver.Chrome(service=Service(driver_path), options=options)
        else:
            self.driver = webdriver.Chrome(options=options)

        self.driver.implicitly_wait(10)

    def _generate_search_url(self, page: int = 1) -> str:
        """Generate search URL with pagination"""
        return f"{self.BASE_URL}/job/latest-and-all-job-ads.php?page={page}&global=1"

    def _extract_company_domain(self, company_name: str) -> str:
        """Generate domain from company name"""
        if not company_name or company_name == "N/A":
            return ""
        # Clean and convert to domain format
        cleaned = re.sub(r'\s+(di|da|de|del|della|)&.*$', '', company_name, flags=re.IGNORECASE)
        cleaned = re.sub(r'[^\w\s]', '', cleaned)
        domain = cleaned.lower().replace(' ', '').strip()
        return f"{domain}.com" if domain else ""

    def _scrape_job_details(self, job_url: str) -> Dict:
        """Scrape detailed job page for employment type and salary"""
        details = {"employment_type": "", "salary": ""}

        try:
            self.driver.get(job_url)
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Look for employment type (contratto, tipo di lavoro)
            for elem in soup.find_all(['span', 'div', 'p']):
                text = elem.get_text(strip=True).lower()
                if any(word in text for word in ['full-time', 'part-time', 'full time', 'part time',
                                                  'tempo pieno', 'part-time', 'determinato', 'indeterminato']):
                    if 'full' in text or 'pieno' in text or 'indeterminato' in text:
                        details["employment_type"] = "Full-time"
                    elif 'part' in text or 'determinato' in text:
                        details["employment_type"] = "Part-time/Contract"
                    break

            # Look for salary (stipendio, retribuzione, €)
            for elem in soup.find_all(['span', 'div', 'p', 'strong']):
                text = elem.get_text(strip=True)
                if '€' in text or ('eur' in text.lower() and any(word in text.lower() for word in ['stipendio', 'retribuzione', 'salary', 'remunerazione'])):
                    details["salary"] = text[:100]
                    break

        except Exception as e:
            pass

        return details

    def scrape_page(self, page: int = 1) -> List[Dict]:
        """Scrape a single page of job listings"""
        url = self._generate_search_url(page)
        print(f"\n📄 Scraping page {page}: {url}")

        self.driver.get(url)
        time.sleep(3)

        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        results = soup.select('.singleResult')

        print(f"   Found {len(results)} job listings")

        jobs = []
        for idx, result in enumerate(results, 1):
            try:
                # Job title
                title_elem = result.select_one('h3')
                title = title_elem.get_text(strip=True) if title_elem else "N/A"

                # Job URL
                link_elem = result.select_one('a[href*="view-job"]')
                if link_elem:
                    job_url = urljoin(self.BASE_URL, link_elem.get('href'))
                else:
                    job_url = "N/A"

                # Company
                company = "N/A"
                company_elem = result.select_one('.companyLink span')
                if company_elem:
                    company = company_elem.get_text(strip=True)

                # Location (from Sede section - clean format)
                location_parts = []
                location_spans = result.select('span')
                for span in location_spans:
                    parent = span.parent
                    if parent and any('sede' in t.get_text().lower() for t in [parent] if t):
                        text = span.get_text(strip=True)
                        # Skip labels and bad values
                        if (text and len(text) > 2 and
                            text.lower() not in ['sede:', 'label', 'nuovo!', 'new', 'sede'] and
                            not span.get('class', []).__contains__('label')):
                            location_parts.append(text)

                # Join location parts and clean
                location = ", ".join(location_parts[:4]) if location_parts else "Italia"
                location = location.replace('Sede:', '').replace('sede:', '').strip()

                # Description (from detailsData)
                description = ""
                desc_elem = result.select_one('.descriptionContainer p')
                if desc_elem:
                    desc_text = desc_elem.get_text(separator=' ', strip=True)
                    # Remove "Nuovo!" and clean whitespace
                    desc_text = re.sub(r'\s+', ' ', desc_text)
                    description = desc_text.replace('Nuovo! ', '').replace('New! ', '').strip()
                    # Limit description length
                    if len(description) > 500:
                        description = description[:500] + "..."

                # Date posted (from .date class)
                date_posted = "Recent"
                date_elem = result.select_one('.date .date, span.date')
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    # Validate it looks like a date (DD/MM/YYYY)
                    if re.match(r'\d{2}/\d{2}/\d{4}', date_text):
                        date_posted = date_text

                # Check keyword filter
                if self.search_keywords:
                    title_lower = title.lower()
                    desc_lower = description.lower()
                    if self.search_keywords not in title_lower and self.search_keywords not in desc_lower:
                        print(f"      [{idx}] ⏭️  Skipped (no keyword match): {title}")
                        continue

                # Get additional details from job page
                job_details = self._scrape_job_details(job_url) if job_url != "N/A" else {}

                # Company domain
                company_domain = self._extract_company_domain(company)

                job_data = {
                    "job_title": title,
                    "company": company,
                    "company_domain": company_domain,
                    "job_location": location,
                    "description": description,
                    "job_post_url": job_url,
                    "date_posted": date_posted,
                    "employment_type": job_details.get("employment_type", "Not specified"),
                    "salary": job_details.get("salary", "Not specified"),
                    "status": "active",
                    "scraped_at": datetime.now().isoformat()
                }

                jobs.append(job_data)
                print(f"      [{idx}] ✅ {title} - {company}")

            except Exception as e:
                print(f"      [{idx}] ❌ Error: {e}")
                continue

        return jobs

    def run(self, output_format: str = "csv"):
        """Run the full scraper"""
        print("=" * 60)
        print("🔍 TROVOLAVORO SCRAPER")
        print("=" * 60)

        self._setup_driver()

        try:
            for page in range(1, self.max_pages + 1):
                jobs = self.scrape_page(page)
                self.scraped_jobs.extend(jobs)

                if len(self.scraped_jobs) >= self.max_jobs:
                    print(f"\n🎯 Reached max jobs limit ({self.max_jobs})")
                    break

                if len(jobs) == 0:
                    print("📋 No more jobs found")
                    break

                time.sleep(2)

            # Save results
            if self.scraped_jobs:
                print("\n" + "=" * 60)
                print(f"✅ TOTAL JOBS SCRAPED: {len(self.scraped_jobs)}")
                print("=" * 60)

                if output_format in ["csv", "both"]:
                    df = pd.DataFrame(self.scraped_jobs)
                    columns_order = ["job_title", "company", "company_domain", "job_location",
                                    "description", "job_post_url", "date_posted",
                                    "employment_type", "salary", "status"]
                    df = df[[col for col in columns_order if col in df.columns]]
                    filename = "trovolavoro_jobs.csv"
                    df.to_csv(filename, index=False, encoding="utf-8")
                    print(f"💾 Saved to {filename}")

                if output_format in ["json", "both"]:
                    import json
                    with open("trovolavoro_jobs.json", "w", encoding="utf-8") as f:
                        json.dump(self.scraped_jobs, f, indent=2, ensure_ascii=False)
                    print(f"💾 Saved to trovolavoro_jobs.json")
            else:
                print("❌ No jobs found")

        finally:
            self.driver.quit()


def main():
    scraper = TrovoLavoroScraper(
        search_keywords="",  # Leave empty for all jobs, or add keyword like "informatica"
        max_pages=3,
        max_jobs=30,
        headless=False
    )
    scraper.run(output_format="csv")


if __name__ == "__main__":
    main()
