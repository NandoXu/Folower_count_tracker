#scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler

class ScrapeScheduler:
    """Schedule recurring scraping jobs."""

    def __init__(self, job_func, interval_minutes=60):
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(job_func, 'interval',
                               minutes=interval_minutes,
                               id='scrape_job')

    def start(self):
        self.scheduler.start()

    def shutdown(self):
        self.scheduler.shutdown()
