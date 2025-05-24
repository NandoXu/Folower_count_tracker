# scraper/tiktok.py
import re, json
import time
import os # Import the os module for path operations
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By # Import By

from .base import Scraper

# Define the folder for failed screenshots
FAILED_SCREENSHOTS_DIR = "tiktok_failed"

class TikTokScraper(Scraper):
    """Headless-browser scraper for TikTok follower counts with enhanced robustness."""

    def scrape(self, link: str) -> int:
        start_time = time.time() # Start timing the scrape operation

        # Extract username early for consistent naming, even if scrape fails
        username_match = re.search(r"tiktok\.com/@([^/?#&]+)", link)
        target_username = username_match.group(1) if username_match else "unknown_user"
        
        # Ensure the failed screenshots directory exists
        if not os.path.exists(FAILED_SCREENSHOTS_DIR):
            os.makedirs(FAILED_SCREENSHOTS_DIR)
            print(f"Created directory: {FAILED_SCREENSHOTS_DIR}")

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu") # Recommended for headless
        options.add_argument("--no-sandbox") # Recommended for headless
        options.add_argument("--disable-dev-shm-usage") # Recommended for Docker/Linux
        # Add a user-agent to mimic a real browser
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36")
        options.add_argument("--window-size=1920,1080") # Add window size for consistent rendering
        options.page_load_strategy = 'eager' # Set page load strategy to eager for faster loading

        driver = None # Initialize driver to None
        MAX_RETRIES = 2 # Number of times to retry scraping a link
        
        for attempt in range(MAX_RETRIES + 1):
            try:
                driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=options
                )
                print(f"Attempt {attempt + 1}: Navigating to TikTok link: {link}")
                
                try:
                    driver.get(link)
                    # Add a small initial wait to allow page to start loading
                    time.sleep(2) # Reduced initial sleep for faster execution
                    
                    # Wait for the body element to be present as a general indicator of page load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    print(f"Page body loaded for {link}.")

                    # Scroll down to ensure dynamic content loads
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1) # Give a moment for content to load after scroll
                    print(f"Scrolled down page for {link}.")

                except Exception as e:
                    print(f"Error navigating to or loading page for {link} on attempt {attempt + 1}: {e}")
                    if driver:
                        # Save screenshot on load error, named by username and attempt
                        screenshot_path = os.path.join(FAILED_SCREENSHOTS_DIR, f"{target_username}_load_error_attempt_{attempt+1}.png")
                        driver.save_screenshot(screenshot_path)
                        print(f"Screenshot saved: {screenshot_path}")
                        driver.quit() # Ensure driver is closed before retrying
                    if attempt < MAX_RETRIES:
                        print(f"Retrying {link} after a delay...")
                        time.sleep(1) # Reduced wait before retrying
                        continue # Go to the next attempt
                    else:
                        raise Exception(f"Failed to load page for {link} after {MAX_RETRIES + 1} attempts.")

                # Parse the rendered HTML
                soup = BeautifulSoup(driver.page_source, "html.parser")

                # 1) Try the SIGI_STATE JSON blob
                script = soup.find("script", id="SIGI_STATE")
                if script and script.string:
                    try:
                        data = json.loads(script.string)
                        # print(f"DEBUG: SIGI_STATE data for {link}: {json.dumps(data, indent=2)}") # Uncomment for debugging
                        
                        user_module = data.get("UserModule", {})
                        users = user_module.get("users", {})
                        
                        if target_username != "unknown_user":
                            # Try to find the user by uniqueId or nickname
                            for user_key, user_data in users.items():
                                if user_data.get("uniqueId") == target_username or user_data.get("nickname") == target_username:
                                    if "stats" in user_data and "followerCount" in user_data["stats"]:
                                        end_time = time.time() # End timing
                                        duration = end_time - start_time
                                        print(f"Successfully scraped follower count for {link} (matched {target_username}) in {duration:.2f} seconds.")
                                        return user_data["stats"]["followerCount"]
                            print(f"Target username '{target_username}' not found in SIGI_STATE users for {link}. Trying first user.")
                        
                        # Fallback if specific user not found by iterating, try to get the first one if it exists
                        first_user_key = next(iter(users), None)
                        if first_user_key and "stats" in users[first_user_key] and "followerCount" in users[first_user_key]["stats"]:
                            end_time = time.time() # End timing
                            duration = end_time - start_time
                            print(f"Found follower count in SIGI_STATE for {link} via first_user_key in {duration:.2f} seconds.")
                            return users[first_user_key]["stats"]["followerCount"]

                    except (json.JSONDecodeError, KeyError, AttributeError) as e:
                        print(f"Error parsing SIGI_STATE JSON for {link}: {e}")
                        # Fall through to fallback if SIGI_STATE parsing fails or if data not found

                print(f"SIGI_STATE method failed or data not found for {link}. Attempting fallback.")

                # 2) Fallback: visible <strong title="Followers"> or similar elements
                try:
                    # Wait for a div that typically contains follower information
                    WebDriverWait(driver, 15).until( 
                        EC.presence_of_element_located((By.XPATH, 
                            "//strong[@title='Followers'] | "
                            "//div[contains(translate(text(), 'F', 'f'), 'followers')] | "
                            "//span[contains(translate(text(), 'F', 'f'), 'followers')] | "
                            "//p[contains(translate(text(), 'F', 'f'), 'followers')]"
                        ))
                    )
                    soup_fallback = BeautifulSoup(driver.page_source, "html.parser") # Re-parse after waiting for elements

                    strong = soup_fallback.find("strong", {"title": "Followers"})
                    if strong:
                        text = strong.get_text(strip=True).upper()
                        print(f"Found strong tag text for {link}: {text}")
                        if text.endswith("M"):
                            end_time = time.time() # End timing
                            duration = end_time - start_time
                            print(f"Scraped follower count via strong tag for {link} in {duration:.2f} seconds.")
                            return int(float(text[:-1]) * 1_000_000)
                        elif text.endswith("K"):
                            end_time = time.time() # End timing
                            duration = end_time - start_time
                            print(f"Scraped follower count via strong tag for {link} in {duration:.2f} seconds.")
                            return int(float(text[:-1]) * 1_000)
                        else:
                            end_time = time.time() # End timing
                            duration = end_time - start_time
                            print(f"Scraped follower count via strong tag for {link} in {duration:.2f} seconds.")
                            return int(text.replace(",", ""))
                    
                    # Broader search for follower count text
                    follower_elements = soup_fallback.find_all(text=re.compile(r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d)?[KkMm]?)\s*followers?", re.IGNORECASE))
                    for elem in follower_elements:
                        match = re.search(r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d)?[KkMm]?)\s*followers?", elem, re.IGNORECASE)
                        if match:
                            num_str = match.group(1).replace(',', '')
                            print(f"Found follower count via regex fallback for {link}: {num_str}")
                            end_time = time.time() # End timing
                            duration = end_time - start_time
                            print(f"Scraped follower count via regex fallback for {link} in {duration:.2f} seconds.")
                            if num_str.endswith("M"):
                                return int(float(num_str[:-1]) * 1_000_000)
                            elif num_str.endswith("K"):
                                return int(float(num_str[:-1]) * 1_000)
                            else:
                                return int(float(num_str)) 

                except Exception as e:
                    print(f"Error during TikTok fallback scraping for {link}: {e}")

                # If both methods fail for the current attempt
                if attempt == MAX_RETRIES:
                    if driver:
                        # Save screenshot on final scrape failure, named by username
                        screenshot_path = os.path.join(FAILED_SCREENSHOTS_DIR, f"{target_username}_scrape_fail.png")
                        driver.save_screenshot(screenshot_path)
                        print(f"Screenshot saved: {screenshot_path}")
                    end_time = time.time() # End timing
                    duration = end_time - start_time
                    print(f"Failed to locate TikTok follower count for {link} after {MAX_RETRIES + 1} attempts. Total time: {duration:.2f} seconds.")
                    raise Exception(f"Could not locate TikTok follower count for {link} using any method after {MAX_RETRIES + 1} attempts.")
                else:
                    print(f"Scraping failed for {link} on attempt {attempt + 1}. Retrying...")
                    # Close driver before retrying
                    if driver:
                        driver.quit()
                    time.sleep(1) 
                    continue 

            except Exception as overall_e:
                print(f"An unhandled error occurred during TikTok scraping for {link}: {overall_e}")
                if attempt == MAX_RETRIES:
                    if driver:
                        # Save screenshot on unhandled error, named by username
                        screenshot_path = os.path.join(FAILED_SCREENSHOTS_DIR, f"{target_username}_unhandled_error.png")
                        driver.save_screenshot(screenshot_path)
                        print(f"Screenshot saved: {screenshot_path}")
                    end_time = time.time() # End timing
                    duration = end_time - start_time
                    print(f"Unhandled error during scrape for {link} after {MAX_RETRIES + 1} attempts. Total time: {duration:.2f} seconds.")
                    raise 
                else:
                    print(f"Scraping failed for {link} on attempt {attempt + 1}. Retrying...")
                    if driver:
                        driver.quit()
                    time.sleep(1) 
                    continue 
            finally:
                if driver:
                    driver.quit()
        
        end_time = time.time() # End timing for unexpected path
        duration = end_time - start_time
        print(f"Unexpected error: TikTok scraper finished without returning a count or raising an exception for {link}. Total time: {duration:.2f} seconds.")
        raise Exception(f"Unexpected error: TikTok scraper finished without returning a count or raising an exception for {link}.")

