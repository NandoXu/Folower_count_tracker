#base.py
from abc import ABC, abstractmethod

class Scraper(ABC):
    """Abstract base class for platform scrapers."""

    @abstractmethod
    def scrape(self, link: str) -> int:
        """Return the follower count for the given link."""
        pass
