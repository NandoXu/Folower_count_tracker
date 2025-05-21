# scraper/x_twitter.py

import sys
import ssl
import re
import time
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import os
os.environ["PYTHONHTTPSVERIFY"] = "0"
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass

# Patch for missing distutils in Python 3.12:
try:
    import distutils
except ModuleNotFoundError:
    try:
        from setuptools import _distutils as distutils
        sys.modules["distutils"] = distutils
    except ModuleNotFoundError:
        raise ModuleNotFoundError(
            "setuptools must be installed. Please run: pip install setuptools"
        )

def parse_number(text: str) -> int:
    """
    Convert a numeric string (which may include commas or abbreviations like K/M) into an integer.

    Examples:
      "12,345" -> 12345
      "12.3K"  -> 12300
      "1.2M"   -> 1200000
    """
    text = text.strip()
    multiplier = 1
    # Check for K or M abbreviations
    if text[-1].lower() == "k":
        multiplier = 1000
        text = text[:-1]
    elif text[-1].lower() == "m":
        multiplier = 1000000
        text = text[:-1]
    try:
        return int(float(text.replace(",", "")) * multiplier)
    except ValueError:
        raise ValueError("Could not parse number from: " + text)

def extract_username(link: str) -> str:
    """
    Extract the username from a full URL or plain text.
    
    Examples:
       "https://x.com/graykolori"  --> "graykolori"
       "@elonmusk"                --> "elonmusk"
    """
    link = link.strip()
    if link.startswith("http"):
        return link.rstrip('/').rsplit('/', 1)[-1].lstrip('@')
    else:
        return link.lstrip('@')

def get_follower_count(username: str) -> int:
    """
    Opens the X (formerly Twitter) profile for the given username using undetected‑chromedriver
    and extracts the follower count. It first tries to wait for the element that normally displays
    the follower count. If that fails (as may be the case with small accounts), it scans the entire
    page text for a pattern matching the number of followers.
    """
    url = f"https://x.com/{username}"
    
    options = Options()
    # Set a modern user agent.
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/117.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    # For troubleshooting, try setting headless=False
    options.headless = True

    service = Service(ChromeDriverManager().install())
    driver = uc.Chrome(options=options, service=service)
    try:
        driver.set_page_load_timeout(20)
        driver.get(url)
        # Wait a few seconds for the page to render.
        time.sleep(5)
        
        # Attempt 1: Use an explicit wait to find the known element.
        try:
            elem = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-testid='UserProfileHeader_Items'] a[href*='/followers'] span")
                )
            )
            text = elem.text.strip()
            if text:
                return parse_number(text)
        except Exception:
            pass

        # Attempt 2: Use an alternative CSS selector.
        try:
            elem = driver.find_element(By.CSS_SELECTOR, "a[href$='/followers'] span")
            text = elem.text.strip()
            if text:
                return parse_number(text)
        except Exception:
            pass

        # Attempt 3: Fallback via regex on the entire page text.
        body_text = driver.find_element(By.TAG_NAME, "body").text
        # Updated regex: allows optional whitespace and also matches singular "Follower"
        m = re.search(r"([\d,\.]+(?:[KkMm])?)\s*Follower[s]?", body_text, flags=re.IGNORECASE)
        if m:
            return parse_number(m.group(1))
        else:
            raise Exception("Could not locate follower count via explicit wait or regex fallback.")
    finally:
        driver.quit()

class XTwitterScraper:
    """
    Scrapes follower counts from X (formerly Twitter) using undetected‑chromedriver.
    """
    def scrape(self, link: str) -> int:
        username = extract_username(link)
        if not username:
            raise ValueError(f"Invalid link or username: '{link}'")
        return get_follower_count(username)

# Standalone testing:
if __name__ == "__main__":
    test_handles = [
        'https://x.com/RAW_RoninArts',
        'nandoxun',
        '@elonmusk'
    ]
    scraper = XTwitterScraper()
    for handle in test_handles:
        try:
            user = extract_username(handle)
            count = scraper.scrape(handle)
            print(f"Follower count for {user}: {count}")
        except Exception as err:
            print(f"Error for {handle}: {err}")
