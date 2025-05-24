#scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import EVENT_SCHEDULER_STARTED, EVENT_SCHEDULER_SHUTDOWN
import sys # Import sys for logging to stderr

class ScrapeScheduler:
    """
    Schedule recurring scraping jobs using APScheduler's BackgroundScheduler.
    Includes state tracking to prevent attempting to shut down a non-running scheduler.
    """

    def __init__(self, job_func, interval_minutes=60):
        """
        Initializes the scheduler.

        Args:
            job_func (callable): The function to be executed by the scheduler.
            interval_minutes (int): The interval in minutes at which the job_func should run.
        """
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(job_func, 'interval',
                               minutes=interval_minutes,
                               id='scrape_job')
        self._is_running = False # Flag to track if the scheduler is active
        
        # Add listeners for scheduler events to update the _is_running flag
        self.scheduler.add_listener(self._scheduler_event_listener,
                                    EVENT_SCHEDULER_STARTED | EVENT_SCHEDULER_SHUTDOWN)

    def _scheduler_event_listener(self, event):
        """
        Internal listener for APScheduler events to update the _is_running flag.
        Corrected: Use event.code instead of event.event_code.
        """
        if event.code == EVENT_SCHEDULER_STARTED: # Corrected from event.event_code
            self._is_running = True
            print("ScrapeScheduler: Scheduler started.")
        elif event.code == EVENT_SCHEDULER_SHUTDOWN: # Corrected from event.event_code
            self._is_running = False
            print("ScrapeScheduler: Scheduler shut down.")

    def start(self):
        """
        Starts the scheduler if it's not already running.
        """
        if not self._is_running:
            try:
                self.scheduler.start()
            except Exception as e:
                print(f"ScrapeScheduler: Error starting scheduler: {e}", file=sys.stderr)
        else:
            print("ScrapeScheduler: Scheduler is already running.")

    def shutdown(self):
        """
        Shuts down the scheduler if it is currently running.
        Prevents SchedulerNotRunningError by checking the _is_running flag.
        """
        if self._is_running:
            print("ScrapeScheduler: Attempting to shut down scheduler...")
            try:
                self.scheduler.shutdown()
            except Exception as e:
                print(f"ScrapeScheduler: Error during scheduler shutdown: {e}", file=sys.stderr)
        else:
            print("ScrapeScheduler: Scheduler is not running, no need to shut down.")

