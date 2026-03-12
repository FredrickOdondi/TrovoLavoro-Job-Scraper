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
        headless: bool = True,
        specific_job_titles: Optional[List[str]] = None
    ):
        self.search_keywords = search_keywords.lower() if search_keywords else ""
        self.max_pages = max_pages
        self.max_jobs = max_jobs
        self.headless = headless
        # Specific job titles to filter - case-insensitive matching
        if specific_job_titles:
            self.specific_job_titles = [t.lower().strip() for t in specific_job_titles]
        else:
            # Load from default file if exists
            self.specific_job_titles = self._load_default_job_titles()

        self.scraped_jobs: List[Dict] = []
        self.driver = None

    def _load_default_job_titles(self) -> List[str]:
        """Load job titles from default configuration file"""
        job_titles_file = os.path.join(os.path.dirname(__file__), "job_titles.txt")
        if os.path.exists(job_titles_file):
            try:
                with open(job_titles_file, 'r', encoding='utf-8') as f:
                    titles = [line.strip().lower() for line in f if line.strip()]
                print(f"   📋 Loaded {len(titles)} job titles from {job_titles_file}")
                return titles
            except Exception as e:
                print(f"   ⚠️  Could not load job_titles.txt: {e}")
        return []

    def _setup_driver(self):
        """Setup Chrome driver with Brave browser"""
        options = Options()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Add options for better stability during long scraping sessions
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        # Extended session stability options
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        # Prevent memory issues in long sessions
        options.add_argument("--max-old-space-size=4096")
        # Longer timeouts
        options.page_load_timeout = 60
        options.script_timeout = 30

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

        # Set page load timeout for individual requests
        self.driver.set_page_load_timeout(60)

    def _is_driver_alive(self) -> bool:
        """Check if the driver session is still alive"""
        try:
            # Try to get the current URL - this will fail if session is invalid
            self.driver.current_url
            return True
        except:
            return False

    def _ensure_driver_alive(self):
        """Ensure the driver is alive, reinitialize if needed"""
        if self.driver is None or not self._is_driver_alive():
            print("   ⚠️  Session lost, reinitializing driver...")
            try:
                if self.driver:
                    self.driver.quit()
            except:
                pass
            self._setup_driver()
            print("   ✅ Driver reinitialized")

    def _restart_driver(self):
        """Force restart the driver to prevent session issues in long runs"""
        print("   🔁 Restarting driver for session stability...")
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
        self._setup_driver()
        print("   ✅ Driver restarted")

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

    def _extract_domain_from_job_page(self, soup: BeautifulSoup) -> str:
        """Extract company domain from job page HTML"""
        # Pattern 1: Look for "Web site:" followed by domain
        for elem in soup.find_all(['p', 'div', 'span', 'strong', 'b']):
            text = elem.get_text(strip=True)
            if 'web site:' in text.lower() or 'website:' in text.lower() or 'sito web:' in text.lower():
                # Extract domain after the label - more restrictive pattern
                for pattern in [r'[wW]eb\s*site:\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?=[^\w.]|$)',
                                 r'[wW]ebsite:\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?=[^\w.]|$)',
                                 r'[Ss]ito\s*[Ww]eb:\s*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})(?=[^\w.]|$)',
                                 r'\*\*([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\*\*']:
                    match = re.search(pattern, text)
                    if match:
                        domain = match.group(1)
                        # Clean and validate domain
                        domain = re.sub(r'[\*\(\)]', '', domain)
                        domain = domain.strip()
                        # Remove any trailing non-domain characters
                        domain = re.sub(r'[^a-zA-Z0-9.-]+$', '', domain)
                        if re.match(r'^(?:www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
                            # Add www. if missing
                            if not domain.startswith('http') and not domain.startswith('www.'):
                                domain = 'www.' + domain
                            return domain

        # Pattern 2: Look for links with company website indicators
        for link in soup.find_all('a', href=True):
            href = link.get('href', '').lower()
            link_text = link.get_text(strip=True).lower()

            # Look for privacy policy links containing the domain
            if any(indicator in link_text for indicator in ['privacy', 'cookie', 'policy', 'informativa']):
                # Extract domain from href if it's external
                if href.startswith('http'):
                    from urllib.parse import urlparse
                    parsed = urlparse(href)
                    domain = parsed.netloc
                    if domain and 'trovolavoro' not in domain:
                        return domain

        # Pattern 3: Look for links with website/web site in text
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            link_text = link.get_text(strip=True)
            if any(indicator in link_text.lower() for indicator in ['web site', 'website', 'sito web']):
                if href.startswith('http'):
                    from urllib.parse import urlparse
                    parsed = urlparse(href)
                    domain = parsed.netloc
                    if domain and 'trovolavoro' not in domain:
                        return domain

        # Pattern 4: Look for any domains mentioned in the page text
        for elem in soup.find_all(['p', 'div', 'span']):
            text = elem.get_text(strip=True)
            # Match common domain patterns - more restrictive
            domains = re.findall(r'(?:www\.)?[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}(?=[\s,;\)\]\"]|$)', text)
            for domain in domains:
                domain = domain.strip()
                # Clean domain - remove trailing non-domain characters
                domain = re.sub(r'[^a-zA-Z0-9.-]+$', '', domain)
                # Filter out invalid domains and common exclusions
                if (domain and 'trovolavoro' not in domain.lower() and
                    not domain.endswith('.png') and not domain.endswith('.jpg') and
                    not domain.endswith('.gif') and not domain.endswith('.pdf') and
                    not domain.startswith('www.preferences.') and
                    re.match(r'^(?:www\.)?[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$', domain)):
                    # Add www. if missing and not already starting with http
                    if not domain.startswith('http') and not domain.startswith('www.'):
                        domain = 'www.' + domain
                    return domain

        return ""

    def _scrape_job_details(self, job_url: str) -> Dict:
        """Scrape detailed job page for employment type, salary, and company domain"""
        details = {"employment_type": "", "salary": "", "company_domain": ""}

        try:
            # Ensure driver is alive before making request
            self._ensure_driver_alive()

            self.driver.get(job_url)
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Extract company domain first
            details["company_domain"] = self._extract_domain_from_job_page(soup)

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

        # Ensure driver is alive before making request
        self._ensure_driver_alive()

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

                # Check keyword filter or specific job titles filter
                title_lower = title.lower()
                desc_lower = description.lower()

                # Check specific job titles first (if provided)
                if self.specific_job_titles:
                    # Split each title into words and match if ANY word from ANY title appears in the site title
                    # This makes matching much more flexible
                    title_words = set()
                    for specific_title in self.specific_job_titles:
                        # Split by common delimiters and get words
                        words = re.findall(r'\b\w+\b', specific_title.lower())
                        title_words.update(words)

                    # Match if any word from our list appears in the job title (minimum 3 chars to avoid short words)
                    title_match = any(word in title_lower and len(word) >= 3 for word in title_words)
                    if not title_match:
                        # Debug: show what we found vs what we're looking for
                        print(f"      [{idx}] ⏭️  Skipped: '{title}' didn't match any filter")
                        continue

                # Check keyword filter (if provided and not using specific titles)
                elif self.search_keywords:
                    if self.search_keywords not in title_lower and self.search_keywords not in desc_lower:
                        print(f"      [{idx}] ⏭️  Skipped (no keyword match): {title}")
                        continue

                # Get additional details from job page
                job_details = self._scrape_job_details(job_url) if job_url != "N/A" else {}

                # Use extracted company domain from job page, fallback to empty string
                company_domain = job_details.get("company_domain", "")

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
                domain_msg = f" ({company_domain})" if company_domain else " (no domain found)"
                print(f"      [{idx}] ✅ {title} - {company}{domain_msg}")

            except Exception as e:
                print(f"      [{idx}] ❌ Error: {e}")
                continue

        return jobs

    def _save_results(self, output_format: str = "csv"):
        """Save the scraped results to file"""
        if not self.scraped_jobs:
            return False

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

        return True

    def run(self, output_format: str = "csv"):
        """Run the full scraper"""
        print("=" * 60)
        print("🔍 TROVOLAVORO SCRAPER")
        print("=" * 60)

        self._setup_driver()

        try:
            for page in range(1, self.max_pages + 1):
                try:
                    # Periodically restart driver every 50 pages to prevent session loss
                    if page > 1 and page % 50 == 0:
                        self._restart_driver()

                    jobs = self.scrape_page(page)
                    self.scraped_jobs.extend(jobs)

                    if len(self.scraped_jobs) >= self.max_jobs:
                        print(f"\n🎯 Reached max jobs limit ({self.max_jobs})")
                        break

                    if len(jobs) == 0:
                        print("📋 No more jobs found")
                        break

                    # Variable delay between pages to avoid throttling
                    delay = 2 + (page % 3)  # Varies between 2-4 seconds
                    time.sleep(delay)

                except Exception as e:
                    print(f"   ❌ Error on page {page}: {e}")
                    # Try to continue by reinitializing driver
                    try:
                        self._restart_driver()
                    except:
                        pass
                    # Continue to next page instead of raising
                    if self.scraped_jobs:
                        print(f"   💾 Current progress: {len(self.scraped_jobs)} jobs scraped")
                    continue

            # Save results
            if self.scraped_jobs:
                self._save_results(output_format)
            else:
                print("❌ No jobs found")

        except Exception as e:
            print(f"\n❌ Scraper encountered an error: {e}")
            if self.scraped_jobs:
                print(f"💾 Partial results saved ({len(self.scraped_jobs)} jobs)")
            raise

        finally:
            try:
                self.driver.quit()
            except:
                pass


def main():
    scraper = TrovoLavoroScraper(
        search_keywords="",  # Leave empty for all jobs, or add keyword like "informatica"
        max_pages=50,
        max_jobs=2000,
        headless=False
    )
    scraper.run(output_format="csv")


if __name__ == "__main__":
    main()
