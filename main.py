import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import init_db, upsert_account, delete_account, fetch_all_accounts, export_csv # Make sure import_csv exists in database.py
from scheduler import ScrapeScheduler
from scraper.instagram import InstagramScraper
from scraper.tiktok import TikTokScraper
from scraper.x_twitter import XTwitterScraper
from ui import AppUI
import csv

class Controller:
    def __init__(self, root):
        # Initialize the database.
        init_db()
        # Set up scrapers for each platform.
        self.scrapers = {
            "instagram": InstagramScraper(),
            "tiktok":    TikTokScraper(),
            "twitter":   XTwitterScraper()
        }
        # Create the UI
        self.ui = AppUI(root, self)
        # Start a scheduler that periodically updates all accounts (every 60 minutes, for example)
        self.scheduler = ScrapeScheduler(self.update_all, interval_minutes=60)
        self.scheduler.start()

    def add_account(self, name, link, platform):
        # Scrape the follower count using the corresponding scraper.
        cnt = self.scrapers[platform].scrape(link)
        category = "macro" if cnt >= 100000 else "micro"
        upsert_account(name, link, platform, cnt, category)
        self.ui.refresh()

    def delete_account(self, link):
        delete_account(link)
        self.ui.refresh()

    def update_all(self):
        accounts = fetch_all_accounts()

        def update_acc(acc):
            name, link, platform, _, _ = acc
            cnt = self.scrapers[platform].scrape(link)
            category = "macro" if cnt >= 100000 else "micro"
            upsert_account(name, link, platform, cnt, category)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(update_acc, acc) for acc in accounts]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print("Error updating account:", e)
        self.ui.refresh()

    def import_csv(self, path):
        """
        Imports accounts from a CSV file and scrapes follower counts.
        This version attempts to infer the platform if it's not explicitly provided
        in the CSV row.
        """
        try:
            with open(path, 'r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)  # Skip the header row (assuming your CSV has one)
                for i, row in enumerate(reader): # Added index 'i' for better error reporting
                    # We now expect at least 2 columns (Name, Link)
                    if len(row) < 2:
                        print(f"Skipping row {i+1}: Not enough columns: {row}")
                        continue

                    name = row[0].strip()
                    link = row[1].strip()

                    platform = "unknown" # Default platform
                    # If the CSV row has a third column, use it as the platform
                    if len(row) >= 3:
                        platform = row[2].strip().lower()
                    else:
                        # Attempt to infer platform from the link if not provided
                        if "instagram.com" in link:
                            platform = "instagram"
                        elif "tiktok.com" in link:
                            platform = "tiktok"
                        elif "x.com" in link or "twitter.com" in link: # Covers both x.com and twitter.com
                            platform = "twitter"
                        else:
                            print(f"Skipping row {i+1}: Could not determine platform for link '{link}'")
                            continue # Skip if platform cannot be determined

                    # Check if the determined platform is valid (i.e., we have a scraper for it).
                    if platform not in self.scrapers:
                        print(f"Skipping row {i+1}: Invalid or unsupported platform '{platform}' for link '{link}'")
                        continue

                    try:
                        # Scrape the follower count using the corresponding scraper.
                        cnt = self.scrapers[platform].scrape(link)
                        category = "macro" if cnt >= 100000 else "micro"
                        upsert_account(name, link, platform, cnt, category)
                    except Exception as e:
                        print(f"Failed to import/scrape: {name}, {link}, {platform} - Error: {e}")
                        upsert_account(name, link, platform, 0, "failed")
            self.ui.refresh()  # Refresh the UI after importing
        except Exception as e:
            # Re-raise the exception with a more informative message for the UI
            raise Exception(f"Error importing CSV file: {e}")

    def export_csv(self):
        export_csv()

    def fetch_all(self):
        return fetch_all_accounts()

    def sort_by(self, tree, col):
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            data.sort(key=lambda t: int(t[0]))
        except ValueError:
            data.sort(key=lambda t: t[0].lower())
        for index, (_, k) in enumerate(data):
            tree.move(k, "", index)

def main():
    root = tk.Tk()
    Controller(root)
    root.mainloop()

if __name__ == '__main__':
    main()
