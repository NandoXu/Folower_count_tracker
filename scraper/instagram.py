# scraper/instagram.py
import re
import time
import os
import sys
import undetected_chromedriver as uc
from datetime import datetime
from selenium.webdriver.common.by import By
from undetected_chromedriver.options import ChromeOptions
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from bs4 import BeautifulSoup

import instaloader
from instaloader import exceptions as InstaloaderExceptions # Alias for easier access

from .base import Scraper

# Define the folder for failed screenshots (for headless browser fallback)
FAILED_SCREENSHOTS_DIR = "instagram_failed"
os.makedirs(FAILED_SCREENSHOTS_DIR, exist_ok=True)

class InstagramScraper(Scraper):
    """
    Scrapes Instagram follower counts using Instaloader first.
    If Instaloader hits rate limits or fails, it falls back to a headless browser (undetected-chromedriver).
    Includes a cooldown mechanism for Instaloader to allow rate limits to reset.
    Note: Unauthenticated Instagram scraping is highly challenging and prone to frequent failures.
    """

    def __init__(self):
        # Initialize Instaloader without login. It will operate in public mode.
        self._initialize_instaloader()
        self._last_instaloader_failure_time = None # Tracks when Instaloader last hit a rate limit
        self._instaloader_cooldown_minutes = 30 # Cooldown period in minutes for Instaloader

    def _initialize_instaloader(self):
        """Initializes or re-initializes the Instaloader instance."""
        print("InstagramScraper: Initializing new Instaloader instance.")
        self.loader = instaloader.Instaloader(
            # Configure Instaloader to minimize resource usage for public scraping
            download_pictures=False,
            download_videos=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern=""
        )

    def _scrape_with_instaloader(self, username: str) -> int:
        """
        Attempts to scrape follower count using Instaloader (unauthenticated).
        Raises InstaloaderExceptions on failure, which can trigger fallback.
        """
        print(f"InstagramScraper: Attempting Instaloader scrape for {username}...")
        profile = instaloader.Profile.from_username(self.loader.context, username)
        followers = profile.followers
        print(f"InstagramScraper: Instaloader successful for {username}: {followers} followers.")
        return followers

    def _scrape_with_headless_browser(self, link: str, target_username: str) -> int:
        """
        Attempts to scrape follower count using a headless browser (undetected-chromedriver).
        This is the fallback method.
        """
        print(f"InstagramScraper: Falling back to headless browser for {target_username} at {link}...")
        
        driver = None
        MAX_BROWSER_RETRIES = 1 # Fewer retries for browser as it's slower

        for attempt in range(MAX_BROWSER_RETRIES + 1):
            try:
                # IMPORTANT FIX: Create new ChromeOptions for each attempt
                options = ChromeOptions()
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
                options.add_argument("--window-size=1920,1080")
                options.page_load_strategy = 'eager'

                driver = uc.Chrome(options=options, use_subprocess=True)
                driver.set_page_load_timeout(30)
                print(f"Browser Attempt {attempt + 1}: Navigating to Instagram link: {link}")
                
                driver.get(link)
                
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                print(f"Browser: Page body loaded for {link}. Giving a short additional wait.")
                time.sleep(3)

                if "accounts.instagram.com/accounts/login" in driver.current_url:
                    raise Exception(f"Browser: Redirected to Instagram login page for {target_username}. Cannot scrape without login.")

                soup = BeautifulSoup(driver.page_source, "html.parser")

                # Attempt 1: Look for follower count in meta tags
                meta_description = soup.find("meta", {"name": "description"})
                if meta_description and meta_description.get("content"):
                    content = meta_description["content"]
                    match = re.search(r"([\d,]+\s*Followers)", content)
                    if match:
                        followers_str = match.group(1).replace(",", "").replace(" Followers", "")
                        followers = int(followers_str)
                        print(f"Browser: Found follower count via meta description for {target_username}: {followers}.")
                        return followers
                
                print(f"Browser: Meta description method failed for {target_username}. Trying element search.")

                # Attempt 2: Search for specific elements that might contain follower count
                try:
                    follower_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, 
                            "//span[contains(translate(text(), 'F', 'f'), 'followers')] | "
                            "//div[contains(translate(text(), 'F', 'f'), 'followers')] | "
                            "//a[contains(@href, '/followers/')]/span"
                        ))
                    )
                    text = follower_element.text
                    match = re.search(r"(\d[\d,.]*[KkMm]?)\s*followers", text, re.IGNORECASE)
                    if match:
                        followers_str = match.group(1).replace(",", "")
                        if followers_str.endswith('K'):
                            followers = int(float(followers_str[:-1]) * 1000)
                        elif followers_str.endswith('M'):
                            followers = int(float(followers_str[:-1]) * 1000000)
                        else:
                            followers = int(followers_str)
                        print(f"Browser: Found follower count via element search for {target_username}: {followers}.")
                        return followers
                except TimeoutException:
                    print(f"Browser: Element search timed out for {target_username}. No direct element found.")
                except Exception as e:
                    print(f"Browser: Error during element search for {target_username}: {e}", file=sys.stderr)

                # If both methods fail for the current attempt
                if attempt == MAX_BROWSER_RETRIES:
                    # Attempt to save screenshot BEFORE raising exception or quitting driver
                    if driver:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = os.path.join(FAILED_SCREENSHOTS_DIR, f"{target_username}_browser_scrape_fail_{timestamp}.png")
                        try:
                            driver.save_screenshot(screenshot_path)
                            print(f"Browser: Screenshot saved to: {screenshot_path}")
                        except Exception as se:
                            print(f"Browser: Failed to save screenshot on scrape failure for {target_username}: {se}", file=sys.stderr)
                    raise Exception(f"Browser: Could not locate Instagram follower count for {target_username} after {MAX_BROWSER_RETRIES + 1} attempts.")
                else:
                    print(f"Browser: Scraping failed for {target_username} on attempt {attempt + 1}. Retrying...")
                    # Driver will be quit in finally block for retries
                    time.sleep(2)
                    continue

            except WebDriverException as we:
                print(f"Browser: WebDriver error during scrape for {target_username}: {we}", file=sys.stderr)
                # Attempt to save screenshot immediately on WebDriver error
                if driver:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(FAILED_SCREENSHOTS_DIR, f"{target_username}_browser_webdriver_error_{timestamp}.png")
                    try:
                        driver.save_screenshot(screenshot_path)
                        print(f"Browser: Screenshot saved to: {screenshot_path}")
                    except Exception as se:
                        print(f"Browser: Failed to save screenshot on WebDriver error for {target_username}: {se}", file=sys.stderr)
                
                if attempt == MAX_BROWSER_RETRIES:
                    raise # Re-raise the original WebDriverException
                else:
                    print(f"Browser: Retrying after WebDriver error for {target_username}...")
                    # Driver will be quit in finally block for retries
                    time.sleep(2)
                    continue
            except Exception as overall_e:
                print(f"Browser: An unhandled error occurred during browser scraping for {target_username}: {overall_e}", file=sys.stderr)
                # Attempt to save screenshot immediately on unhandled error
                if driver:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(FAILED_SCREENSHOTS_DIR, f"{target_username}_browser_unhandled_error_{timestamp}.png")
                    try:
                        driver.save_screenshot(screenshot_path)
                        print(f"Browser: Screenshot saved to: {screenshot_path}")
                    except Exception as se:
                        print(f"Browser: Failed to save screenshot on unhandled error for {target_username}: {se}", file=sys.stderr)

                if attempt == MAX_BROWSER_RETRIES:
                    raise # Re-raise the original unhandled exception
                else:
                    print(f"Browser: Retrying after unhandled error for {target_username}...")
                    # Driver will be quit in finally block for retries
                    time.sleep(2)
                    continue
            finally:
                if driver:
                    try:
                        driver.quit()
                        print(f"Browser: Driver quit successfully for {target_username}.")
                    except Exception as e:
                        print(f"Browser: Error quitting driver for {target_username}: {e}", file=sys.stderr)
        
        # This line should ideally not be reached if exceptions are handled correctly
        raise Exception(f"Browser: Unexpected error: scraper finished without returning a count or raising an exception for {target_username}.")


    def scrape(self, link: str) -> int:
        """
        Attempts to scrape Instagram follower count using Instaloader first.
        Falls back to a headless browser if Instaloader fails (e.g., due to rate limits).
        """
        start_time = time.time()
        username_match = re.search(r"instagram\.com/([^/?#&]+)", link)
        target_username = username_match.group(1) if username_match else "unknown_user"
        
        if not target_username:
            raise ValueError(f"Invalid Instagram URL: {link}")

        # Check if Instaloader is on cooldown
        if (self._last_instaloader_failure_time is not None and
            (time.time() - self._last_instaloader_failure_time) / 60 < self._instaloader_cooldown_minutes):
            
            remaining_cooldown = int(self._instaloader_cooldown_minutes - (time.time() - self._last_instaloader_failure_time) / 60)
            print(f"InstagramScraper: Instaloader is on cooldown for {remaining_cooldown} more minutes. Skipping Instaloader and falling back to browser.")
            # Directly proceed to browser scraping
        else:
            # If cooldown has passed, re-initialize Instaloader for a fresh context
            if self._last_instaloader_failure_time is not None:
                print("InstagramScraper: Instaloader cooldown period ended. Re-initializing Instaloader.")
                self._initialize_instaloader()
                self._last_instaloader_failure_time = None # Reset failure time

            try:
                # Attempt with Instaloader first
                followers = self._scrape_with_instaloader(target_username)
                return followers
            except InstaloaderExceptions.QueryReturnedBadRequestException as e:
                print(f"InstagramScraper: Instaloader hit rate limit or bad request for {target_username}: {e}. Setting cooldown and falling back to browser.")
                self._last_instaloader_failure_time = time.time() # Record failure time
                # Fall through to browser scraping
            except InstaloaderExceptions.ProfileNotExistsException:
                print(f"InstagramScraper: Instaloader: Profile '{target_username}' does not exist. Falling back to browser (though it might also fail).")
                # Fall through to browser scraping
            except InstaloaderExceptions.PrivateProfileNotFollowedException:
                print(f"InstagramScraper: Instaloader: Profile '{target_username}' is private. Falling back to browser (will likely fail for private profiles).")
                # Fall through to browser scraping
            except InstaloaderExceptions.InstaloaderException as e:
                print(f"InstagramScraper: Instaloader experienced an unexpected error for {target_username}: {e}. Falling back to browser.")
                # Fall through to browser scraping
            except Exception as e:
                print(f"InstagramScraper: An unexpected non-Instaloader error occurred with Instaloader for {target_username}: {e}. Falling back to browser.")
                # Fall through to browser scraping

        # If Instaloader failed or was on cooldown, then try with headless browser
        try:
            followers = self._scrape_with_headless_browser(link, target_username)
            return followers
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            print(f"InstagramScraper: Both Instaloader and browser scraping failed for {target_username}. Total time: {duration:.2f} seconds.")
            raise Exception(f"Failed to scrape Instagram followers for {target_username} using both methods: {e}")

# Standalone testing (optional, for local testing)
if __name__ == "__main__":
    scraper = InstagramScraper()
    test_links = [
        "https://www.instagram.com/instagram/", # Example public profile
        "https://www.instagram.com/nonexistent_user_12345/", # Example non-existent profile
        # Add a link that might trigger rate limit if run repeatedly
        # "https://www.instagram.com/nasa/", 
    ]

    for link in test_links:
        print(f"\n--- Testing: {link} ---")
        try:
            followers = scraper.scrape(link)
            print(f"FINAL RESULT for {link}: {followers} followers.")
        except Exception as e:
            print(f"FINAL ERROR for {link}: {e}")
