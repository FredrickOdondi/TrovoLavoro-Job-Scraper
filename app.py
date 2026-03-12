"""
Flask Web UI for TrovoLavoro Job Scraper
Run with: python app.py
Then visit: http://127.0.0.1:5000
"""

import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from trovolavoro_scrapper import TrovoLavoroScraper

app = Flask(__name__)

# Global state for scraping progress
scraping_state = {
    "status": "idle",
    "progress": 0,
    "total_jobs": 0,
    "scraped_jobs": 0,
    "current_phase": "",
    "message": "",
    "results": [],
    "started_at": None
}


@app.route('/')
def index():
    """Main page with configuration form"""
    return render_template('index.html')


@app.route('/api/start', methods=['POST'])
def start_scraping():
    """Start the scraping process in background"""
    data = request.json

    # Reset state
    scraping_state.update({
        "status": "running",
        "progress": 0,
        "total_jobs": 0,
        "scraped_jobs": 0,
        "current_phase": "Initializing",
        "message": "Starting scraper...",
        "results": [],
        "started_at": datetime.now().isoformat()
    })

    # Parse specific job titles from textarea
    # If empty, will use default job_titles.txt file
    job_titles_input = data.get("specific_job_titles", "")
    specific_job_titles = None  # Use default file
    if job_titles_input.strip():  # Only override if user pasted something
        specific_job_titles = [t.strip() for t in job_titles_input.split('\n') if t.strip()]

    # Start scraping in background thread
    thread = threading.Thread(
        target=run_scraper,
        kwargs={
            "search_keywords": data.get("keywords", ""),
            "max_pages": int(data.get("max_pages", 1000)),
            "max_jobs": int(data.get("max_jobs", 20000)),
            "headless": data.get("headless", True),
            "specific_job_titles": specific_job_titles
        }
    )
    thread.daemon = True
    thread.start()

    return jsonify({"status": "started"})


@app.route('/api/status')
def get_status():
    """Get current scraping status and results"""
    return jsonify(scraping_state)


@app.route('/api/export/csv')
def export_csv():
    """Export results as CSV"""
    import pandas as pd
    from flask import Response

    if not scraping_state["results"]:
        return "No results to export", 400

    df = pd.DataFrame(scraping_state["results"])

    columns_order = [
        "job_title", "company", "company_domain", "job_location",
        "description", "job_post_url", "date_posted",
        "employment_type", "salary", "status"
    ]
    df = df[[col for col in columns_order if col in df.columns]]

    csv = df.to_csv(index=False)

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=trovolavoro_jobs.csv"}
    )


@app.route('/api/export/json')
def export_json():
    """Export results as JSON"""
    from flask import Response

    if not scraping_state["results"]:
        return "No results to export", 400

    return Response(
        json.dumps(scraping_state["results"], indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=trovolavoro_jobs.json"}
    )


def update_state(**kwargs):
    """Update scraping state"""
    scraping_state.update(kwargs)


def run_scraper(**kwargs):
    """Run the scraper and update state"""
    try:
        update_state(current_phase="Scraping", message="Fetching job listings...")

        class ProgressScraper(TrovoLavoroScraper):

            def scrape_page(self, page: int = 1):
                update_state(message=f"Scraping page {page}...")
                jobs = super().scrape_page(page)
                update_state(
                    scraped_jobs=len(self.scraped_jobs),
                    total_jobs=min(len(self.scraped_jobs) + 15, self.max_jobs)
                )
                return jobs

            def run(self, output_format="csv"):
                self._setup_driver()

                try:
                    for page in range(1, self.max_pages + 1):
                        try:
                            # Periodically restart driver every 50 pages to prevent session loss
                            if page > 1 and page % 50 == 0:
                                update_state(message=f"Restarting browser for stability...")
                                try:
                                    self._restart_driver()
                                except:
                                    pass

                            jobs = self.scrape_page(page)
                            self.scraped_jobs.extend(jobs)
                            update_state(results=self.scraped_jobs.copy())

                            if len(self.scraped_jobs) >= self.max_jobs:
                                break

                            if len(jobs) == 0:
                                break

                            # Variable delay between pages to avoid throttling
                            delay = 2 + (page % 3)  # Varies between 2-4 seconds
                            time.sleep(delay)

                        except Exception as e:
                            # Try to continue instead of crashing
                            try:
                                self._restart_driver()
                            except:
                                pass
                            update_state(
                                message=f"Error on page {page}: {str(e)}. Retrying..."
                            )
                            # Continue to next page
                            continue

                    # Final update
                    update_state(
                        results=self.scraped_jobs,
                        total_jobs=len(self.scraped_jobs),
                        scraped_jobs=len(self.scraped_jobs),
                        progress=100,
                        status="completed",
                        message=f"Completed! Scraped {len(self.scraped_jobs)} jobs."
                    )

                finally:
                    self.driver.quit()

        scraper = ProgressScraper(**kwargs)
        scraper.run()

    except Exception as e:
        import traceback
        update_state(
            status="error",
            message=f"Error: {str(e)}\n{traceback.format_exc()}"
        )


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 TrovoLavoro Job Scraper Web UI")
    print("=" * 60)
    print("📱 Open your browser to: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000)
