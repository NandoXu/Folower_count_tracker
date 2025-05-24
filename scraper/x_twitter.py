import sys
import ssl
import re
import time
import undetected_chromedriver as uc
import os
from datetime import datetime # Import datetime for timestamp

from selenium.webdriver.common.by import By
# IMPORTANT: Use ChromeOptions from undetected_chromedriver, not selenium.webdriver.chrome.options
from undetected_chromedriver.options import ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

# Define a directory for debug screenshots and ensure it exists
DEBUG_DIR = "x_failed"
os.makedirs(DEBUG_DIR, exist_ok=True)

# Disable SSL verification (use with caution, for specific environments)
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
        # Remove commas, convert to float (to handle "12.3K"), then to int
        return int(float(text.replace(",", "")) * multiplier)
    except ValueError:
        raise ValueError("Could not parse number from: " + text)

def extract_username(link: str) -> str:
    """
    Extract the username from a full URL or plain text.
    
    Examples:
        "https://x.com/graykolori"  --> "graykolori"
        "@elonmusk"                  --> "elonmusk"
    """
    link = link.strip()
    if link.startswith("http"):
        # Remove trailing slash and then split by the last slash to get the username
        return link.rstrip('/').rsplit('/', 1)[-1].lstrip('@')
    else:
        # If it's just a handle, remove the leading '@'
        return link.lstrip('@')

def get_follower_count(username: str) -> int:
    """
    Opens the X (formerly Twitter) profile for the given username using undetected-chromedriver
    and extracts the follower count. It first tries to wait for the element that normally displays
    the follower count. If that fails (as may be the case with small accounts), it scans the entire
    page text for a pattern matching the number of followers.
    """
    url = f"https://x.com/{username}"
    print(f"XTwitterScraper: Starting scrape for {username} at {url}")
    
    # Use undetected_chromedriver's ChromeOptions
    options = ChromeOptions()
    # Set a modern user agent to mimic a real browser
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/117.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled") # To avoid detection
    options.add_argument("--no-sandbox") # Recommended for headless environments
    options.headless = True # Ensure headless mode is true

    driver = None # Initialize driver to None for proper cleanup in finally block
    try:
        # Initialize undetected_chromedriver
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.set_page_load_timeout(30) # Increased timeout for page load
        
        print(f"XTwitterScraper: Navigating to {url}")
        driver.get(url)
        
        # Wait for the body element to be present as a general indicator of page load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        print(f"XTwitterScraper: Page body loaded for {username}. Giving a short additional wait.")
        time.sleep(2) # A short additional wait after initial load for dynamic content

        # Attempt 1: Use an explicit wait to find the known element for followers.
        # This selector targets the span containing the follower count within the profile header.
        try:
            elem = WebDriverWait(driver, 10).until( # Shorter wait for specific element
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[data-testid='UserProfileHeader_Items'] a[href*='/followers'] span")
                )
            )
            text = elem.text.strip()
            if text:
                print(f"XTwitterScraper: Found follower count via CSS selector 1 for {username}: {text}")
                return parse_number(text)
        except TimeoutException:
            print(f"XTwitterScraper: CSS selector 1 timed out for {username}. Trying next method.")
            pass # Continue to next attempt

        # Attempt 2: Use an alternative CSS selector (more general link to followers).
        try:
            elem = driver.find_element(By.CSS_SELECTOR, "a[href$='/followers'] span")
            text = elem.text.strip()
            if text:
                print(f"XTwitterScraper: Found follower count via CSS selector 2 for {username}: {text}")
                return parse_number(text)
        except Exception:
            print(f"XTwitterScraper: CSS selector 2 failed for {username}. Trying regex fallback.")
            pass # Continue to next attempt

        # Attempt 3: Fallback via regex on the entire page text.
        # This is useful for smaller accounts or when the DOM structure changes.
        body_text = driver.find_element(By.TAG_NAME, "body").text
        # Updated regex: allows optional whitespace and also matches singular "Follower"
        # It looks for a number (with optional commas/decimals and K/M suffix) followed by "Follower" or "Followers".
        m = re.search(r"([\d,\.]+(?:[KkMm])?)\s*Follower[s]?", body_text, flags=re.IGNORECASE)
        if m:
            follower_count_str = m.group(1)
            print(f"XTwitterScraper: Found follower count via regex fallback for {username}: {follower_count_str}")
            return parse_number(follower_count_str)
        else:
            raise Exception("Could not locate follower count via explicit wait or regex fallback.")

    except WebDriverException as we:
        print(f"XTwitterScraper: WebDriver error during scrape for {username}: {we}", file=sys.stderr)
        # Capture a timestamp for the screenshot file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if driver: # Only attempt to save screenshot if driver was successfully initialized
            screenshot_path = os.path.join(DEBUG_DIR, f"{username}_failure_{timestamp}.png")
            try:
                driver.save_screenshot(screenshot_path)
                print(f"XTwitterScraper: Error occurred for {username}. Screenshot saved to: {screenshot_path}")
            except Exception as se:
                print(f"XTwitterScraper: Failed to save screenshot for {username}: {se}")
        raise # Re-raise the original exception
    except Exception as e:
        print(f"XTwitterScraper: An unexpected error occurred during scrape for {username}: {e}", file=sys.stderr)
        # Capture a timestamp for the screenshot file name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if driver: # Only attempt to save screenshot if driver was successfully initialized
            screenshot_path = os.path.join(DEBUG_DIR, f"{username}_failure_{timestamp}.png")
            try:
                driver.save_screenshot(screenshot_path)
                print(f"XTwitterScraper: Error occurred for {username}. Screenshot saved to: {screenshot_path}")
            except Exception as se:
                print(f"XTwitterScraper: Failed to save screenshot for {username}: {se}")
        raise # Re-raise the original exception
    finally:
        if driver:
            try:
                driver.quit()
                print(f"XTwitterScraper: Driver quit successfully for {username}.")
            except Exception as e:
                print(f"XTwitterScraper: Error quitting driver for {username}: {e}", file=sys.stderr)

class XTwitterScraper:
    """
    Scrapes follower counts from X (formerly Twitter) using undetected-chromedriver.
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
        '@elonmusk',
        'nonexistentuser12345' # Added a test case for a non-existent user
    ]
    scraper = XTwitterScraper()
    for handle in test_handles:
        try:
            user = extract_username(handle)
            count = scraper.scrape(handle)
            print(f"Follower count for {user}: {count}")
        except Exception as err:
            print(f"Error for {handle}: {err}")
