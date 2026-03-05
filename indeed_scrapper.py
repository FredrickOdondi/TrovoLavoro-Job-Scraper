"""
Indeed Scrapper & Crawler
Uses Selenium with locally installed ChromeDriver (no downloads needed)
"""

import time
import re
import random
import os
from datetime import datetime
from typing import List, Dict, Set, Optional

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


class IndeedCrawlerScraper:
    """
    Combined Crawler + Scraper for Indeed job listings
    """

    BASE_URL = "https://www.indeed.com"

    def __init__(
        self,
        search_keywords: str,
        search_location: str,
        description_keywords: Optional[List[str]] = None,
        max_pages: int = 10,
        max_jobs: int = 100,
        headless: bool = True
    ):
        self.search_keywords = search_keywords
        self.search_location = search_location
        self.description_keywords = description_keywords or []
        self.max_pages = max_pages
        self.max_jobs = max_jobs
        self.headless = headless

        self.job_urls: Set[str] = set()
        self.scraped_jobs: List[Dict] = []
        self.driver = None

    def _setup_driver(self):
        """Setup Chrome driver with Brave browser"""
        options = Options()

        if self.headless:
            options.add_argument("--headless=new")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--profile-directory=Default")
        options.add_argument("--disable-plugins-discovery")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Set Brave browser binary
        brave_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
        if os.path.exists(brave_path):
            options.binary_location = brave_path
            print(f"Using browser: {brave_path}")

        # Use ChromeDriver 145 that matches Brave version
        driver_path = os.path.expanduser("~/chromedriver145")
        if os.path.exists(driver_path):
            print(f"Using ChromeDriver 145: {driver_path}")
            self.driver = webdriver.Chrome(service=Service(driver_path), options=options)
        else:
            print("ChromeDriver 145 not found, trying Selenium Manager...")
            self.driver = webdriver.Chrome(options=options)

        self.driver.implicitly_wait(10)

    def _generate_search_url(self, start: int = 0) -> str:
        from urllib.parse import quote
        base = f"{self.BASE_URL}/jobs"
        params = {"q": self.search_keywords, "l": self.search_location, "start": start}
        query_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
        return f"{base}?{query_string}"

    def _random_delay(self, min_sec=1, max_sec=3):
        time.sleep(random.uniform(min_sec, max_sec))

    def crawl_search_pages(self) -> Set[str]:
        print("=" * 60)
        print("🔍 CRAWLER PHASE: Discovering job URLs...")
        print("=" * 60)

        self._setup_driver()

        try:
            for page in range(self.max_pages):
                start = page * 10
                search_url = self._generate_search_url(start)
                print(f"\n📄 Crawling page {page + 1}: {search_url}")

                self.driver.get(search_url)
                time.sleep(3)

                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                job_cards = soup.select('a[data-jk]')

                print(f"   Found {len(job_cards)} job cards")

                new_count = 0
                for card in job_cards:
                    job_id = card.get('data-jk')
                    if job_id:
                        job_url = f"{self.BASE_URL}/viewjob?jk={job_id}"
                        if job_url not in self.job_urls:
                            self.job_urls.add(job_url)
                            new_count += 1

                print(f"   ✅ Added {new_count} new job URLs (total: {len(self.job_urls)})")

                if len(self.job_urls) >= self.max_jobs:
                    print(f"\n🎯 Reached max jobs limit ({self.max_jobs})")
                    break

                # Check for next page
                if not soup.select_one('a[aria-label="Next Page"]'):
                    print("📋 No more pages available")
                    break

                self._random_delay(2, 4)

        finally:
            print(f"\n✅ CRAWLING COMPLETE: {len(self.job_urls)} job URLs")
            print("=" * 60)

        return self.job_urls

    def extract_company_domain(self, company_name: str) -> str:
        if not company_name:
            return ""
        cleaned = re.sub(r'\s+(Inc|LLC|Corp|Company|Ltd|Technologies|Solutions)\.?$', '', company_name, flags=re.IGNORECASE).strip()
        domain = cleaned.lower().replace(' ', '').replace(',', '').replace("'", "")
        return f"{domain}.com" if domain and '.' not in domain else domain

    def filter_by_description_keywords(self, description: str) -> bool:
        if not self.description_keywords:
            return True
        if not description:
            return False
        desc_lower = description.lower()
        return any(keyword.lower() in desc_lower for keyword in self.description_keywords)

    def scrape_job_details(self, job_url: str) -> Optional[Dict]:
        try:
            print(f"   🔗 Scraping: {job_url}")
            self.driver.get(job_url)
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            job_title = ""
            if t := soup.select_one('h1[class*="jobTitle"], [class*="JobInfoHeader-title"]'):
                job_title = t.get_text(strip=True)

            company = ""
            if c := soup.select_one('[data-testid="inlineHeader-companyName"], [class*="companyName"]'):
                company = c.get_text(strip=True).split('\n')[0].strip()

            company_domain = self.extract_company_domain(company)

            location = ""
            if l := soup.select_one('[data-testid="job-location"], [class*="jobLocation"]'):
                location = l.get_text(strip=True)

            description = ""
            if d := soup.select_one('#jobDescriptionText, [class*="jobDescription"]'):
                description = d.get_text(strip=True)

            if not self.filter_by_description_keywords(description):
                print(f"      ⏭️  Skipped (doesn't match description keywords)")
                return None

            date_posted = ""
            if d := soup.select_one('[data-testid="job-age"], [class*="job-age"]'):
                date_posted = d.get_text(strip=True)

            employment_type = ""
            if et := soup.select_one('[data-testid="job-type"], [class*="job-type"]'):
                employment_type = et.get_text(strip=True)

            salary = ""
            if s := soup.select_one('[data-testid="job-salary"], [class*="job-salary"], .salary-snippet'):
                salary = s.get_text(strip=True)

            job_data = {
                "job_title": job_title,
                "company": company,
                "company_domain": company_domain,
                "job_location": location,
                "description": description,
                "job_post_url": job_url,
                "date_posted": date_posted,
                "employment_type": employment_type,
                "salary": salary,
                "status": "active",
                "scraped_at": datetime.now().isoformat()
            }

            print(f"      ✅ Scraped: {job_title} at {company}")
            return job_data

        except Exception as e:
            print(f"      ❌ Error: {e}")
            return None

    def scrape_all_jobs(self) -> List[Dict]:
        print("\n" + "=" * 60)
        print("📊 SCRAPER PHASE: Extracting job details...")
        print("=" * 60)

        for idx, job_url in enumerate(self.job_urls, 1):
            print(f"[{idx}/{len(self.job_urls)}]", end=" ")
            if job := self.scrape_job_details(job_url):
                self.scraped_jobs.append(job)
            self._random_delay(1, 2)

        print(f"\n✅ SCRAPING COMPLETE: {len(self.scraped_jobs)} jobs extracted")
        print("=" * 60)
        return self.scraped_jobs

    def save_to_csv(self, filename: str = "indeed_jobs.csv"):
        if not self.scraped_jobs:
            return
        df = pd.DataFrame(self.scraped_jobs)
        columns_order = ["job_title", "company", "company_domain", "job_location",
                        "description", "job_post_url", "date_posted", "employment_type", "salary", "status"]
        df = df[[col for col in columns_order if col in df.columns]]
        df.to_csv(filename, index=False, encoding="utf-8")
        print(f"\n💾 Saved {len(df)} jobs to {filename}")

    def save_to_json(self, filename: str = "indeed_jobs.json"):
        if not self.scraped_jobs:
            return
        import json
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.scraped_jobs, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved {len(self.scraped_jobs)} jobs to {filename}")

    def close(self):
        if self.driver:
            self.driver.quit()

    def run(self, output_format: str = "csv"):
        try:
            self.crawl_search_pages()
            if not self.job_urls:
                print("❌ No jobs found.")
                return
            self.scrape_all_jobs()
            if not self.scraped_jobs:
                print("❌ No jobs were successfully scraped.")
                return

            print("\n" + "=" * 60)
            print("💾 SAVING RESULTS...")
            print("=" * 60)
            if output_format in ["csv", "both"]:
                self.save_to_csv()
            if output_format in ["json", "both"]:
                self.save_to_json()

            print("\n" + "=" * 60)
            print("📊 SUMMARY")
            print("=" * 60)
            print(f"Total URLs crawled: {len(self.job_urls)}")
            print(f"Total jobs scraped: {len(self.scraped_jobs)}")
            print(f"Search: {self.search_keywords} in {self.search_location}")
            print("=" * 60)
        finally:
            self.close()


def main():
    scraper = IndeedCrawlerScraper(
        search_keywords="software engineer",
        search_location="San Francisco, CA",
        description_keywords=[],
        max_pages=2,
        max_jobs=20,
        headless=False
    )
    scraper.run(output_format="csv")


if __name__ == "__main__":
    main()
