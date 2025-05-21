# scraper/tiktok.py
import re, json, time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from .base import Scraper

class TikTokScraper(Scraper):
    """Headless‑browser scraper for TikTok follower counts."""

    def scrape(self, link: str) -> int:
        # 1) Launch headless Chrome
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        driver.get(link)
        time.sleep(3)  # let JS run

        # 2) Parse the rendered HTML
        soup = BeautifulSoup(driver.page_source, "html.parser")
        driver.quit()

        # 3) Try the SIGI_STATE JSON blob
        script = soup.find("script", id="SIGI_STATE")
        if script and script.string:
            data = json.loads(script.string)
            user = re.search(r"@([^/?#&]+)", link).group(1)
            return data["UserModule"]["users"][user]["stats"]["followerCount"]

        # 4) Fallback: visible <strong title="Followers">
        strong = soup.find("strong", {"title": "Followers"})
        text = strong.get_text(strip=True).upper()
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        if text.endswith("K"):
            return int(float(text[:-1]) * 1_000)
        return int(text)
