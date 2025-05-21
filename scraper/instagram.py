#instagram.py
import re
import instaloader
from .base import Scraper

class InstagramScraper(Scraper):
    """Scrapes Instagram via Instaloader."""

    def __init__(self):
        self.loader = instaloader.Instaloader()

    def scrape(self, link: str) -> int:
        m = re.search(r"instagram\.com/([^/?#&]+)", link)
        if not m:
            raise ValueError("Invalid Instagram URL")
        username = m.group(1)
        profile = instaloader.Profile.from_username(
            self.loader.context, username)
        return profile.followers
