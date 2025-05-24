# main.py
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
from database import init_db, upsert_account, delete_account, fetch_all_accounts, bulk_upsert_accounts, auto_detect_platform, export_csv_to_file
from scheduler import ScrapeScheduler
from scraper.instagram import InstagramScraper
from scraper.tiktok import TikTokScraper
from scraper.x_twitter import XTwitterScraper
from ui import AppUI
import csv
import random
import time
import sys # Import sys for better error handling/feedback
from tkinter import filedialog # Import filedialog for file dialog operations

class Controller:
    def __init__(self, root):
        init_db()
        self.scrapers = {
            "instagram": InstagramScraper(),
            "tiktok":    TikTokScraper(),
            "twitter":   XTwitterScraper()
        }
        self.ui = AppUI(root, self)
        # Initialize scheduler with a default interval of 60 minutes
        self.scheduler = ScrapeScheduler(self.update_all, interval_minutes=60)
        self.scheduler.start()

        # Set up cleanup for when the window is closed
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        """
        Handle application shutdown.
        This method is called when the Tkinter window is closed.
        It ensures the background scheduler is shut down cleanly.
        Individual scraper drivers (like for XTwitterScraper or TikTokScraper)
        are managed
        """
        print("Shutting down scheduler...")
        self.scheduler.shutdown()
        # Optionally, close any persistent scraper drivers here if they exist
        # For example:
        # if hasattr(self.scrapers.get("x_twitter"), 'driver') and self.scrapers["x_twitter"].driver:
        #     self.scrapers["x_twitter"].driver.quit()
        print("Application closing.")
        self.ui.root.destroy()
        sys.exit(0) # Ensure the application exits cleanly

    def add_account(self, name, link, platform):
        """
        Adds a new account to the database and attempts to scrape it.
        Includes strict platform validation.
        """
        print(f"Controller: Attempting to add account: Name='{name}', Link='{link}', Platform='{platform}'")
        
        # 1. Validate the selected platform itself
        if platform.lower() not in self.scrapers:
            tk.messagebox.showerror("Platform Error", f"Unsupported platform selected: '{platform}'. Please choose from Instagram, TikTok, or Twitter.")
            print(f"Controller: Add failed - Unsupported platform selected: {platform}", file=sys.stderr)
            return

        # 2. Auto-detect platform from the link
        detected_platform = auto_detect_platform(link)
        
        # 3. Compare selected platform with detected platform
        if detected_platform and detected_platform.lower() != platform.lower():
            tk.messagebox.showerror("Platform Mismatch", f"The link '{link}' appears to be for '{detected_platform}', but you selected '{platform}'. Please correct the platform selection.")
            print(f"Controller: Add failed - Platform mismatch: Link detected as '{detected_platform}', selected as '{platform}'", file=sys.stderr)
            return
        
        # If no detected platform, but selected platform is valid, proceed.
        # This handles cases where auto_detect_platform might not catch it, but the user explicitly chose correctly.
        if not detected_platform and platform.lower() not in self.scrapers:
            tk.messagebox.showerror("Platform Error", f"Could not determine platform from link '{link}'. Please ensure the link is valid for '{platform}'.")
            print(f"Controller: Add failed - Could not determine platform from link {link} for selected {platform}", file=sys.stderr)
            return

        try:
            # Add with initial placeholder data
            upsert_account(name, link, platform, 0, "pending")
            self.ui.refresh() # Refresh UI to show the new 'pending' account immediately

            # Scrape the newly added account in a separate thread
            threading.Thread(target=self._scrape_and_update_single_account, args=(link,)).start()
            
        except Exception as e:
            print(f"Controller: Error adding or initiating scrape for account {name}: {e}", file=sys.stderr)
            tk.messagebox.showerror("Error", f"Failed to add account: {e}")

    def _scrape_and_update_single_account(self, link):
        """
        Internal helper to scrape a single account by its link and update the DB.
        Designed to be run in a separate thread.
        """
        try:
            # Fetch the account details from DB to get name and platform
            all_accounts = fetch_all_accounts()
            account_to_scrape = next((acc for acc in all_accounts if acc[1] == link), None)

            if account_to_scrape:
                name, link, platform, _, _ = account_to_scrape
                
                # At this point, platform should already be validated by add_account or import_csv.
                # Just ensure a scraper exists for the given platform.
                scraper = self.scrapers.get(platform)
                if scraper:
                    print(f"Controller: Scraping {platform} account: {link}")
                    try:
                        followers = scraper.scrape(link)
                        category = self._determine_category(followers)
                        upsert_account(name, link, platform, followers, category)
                        print(f"Controller: Successfully scraped {name} ({platform}): {followers} followers, category {category}")
                    except Exception as scrape_e:
                        print(f"Controller: Scraping failed for {link}: {scrape_e}", file=sys.stderr)
                        upsert_account(name, link, platform, 0, "failed") # Mark as failed
                else:
                    # This block should ideally not be hit if initial validation is robust.
                    print(f"Controller: Unexpected: Scraper not found for platform {platform} for link {link}. Marking as failed.", file=sys.stderr)
                    upsert_account(name, link, platform, 0, "failed") # Fallback to generic failed
            else:
                print(f"Controller: Account with link {link} not found for scraping.", file=sys.stderr)
        except Exception as e:
            print(f"Controller: Unexpected error in _scrape_and_update_single_account for {link}: {e}", file=sys.stderr)
        finally:
            self.ui.root.after(0, self.ui.refresh) # Always refresh UI on main thread after attempt

    def delete_account(self, link):
        """
        Deletes an account from the database.
        """
        print(f"Controller: Deleting account with link: {link}")
        try:
            delete_account(link)
            self.ui.refresh()
            print(f"Controller: Account {link} deleted successfully.")
        except Exception as e:
            print(f"Controller: Error deleting account {link}: {e}", file=sys.stderr)
            tk.messagebox.showerror("Error", f"Failed to delete account: {e}")

    def _determine_category(self, followers: int) -> str:
        """
        Determines the category based on the number of followers.
        Corrected to include all categories: mega, macro, mid, micro, nano.
        """
        if followers >= 100000:
            return "macro"
        else:
            return "micro"

    def update_all(self):
        """
        Fetches all accounts and initiates scraping for each, updating their data.
        This is typically called by the scheduler.
        """
        print("Controller: Initiating update for all accounts...")
        accounts_to_update = fetch_all_accounts()
        if not accounts_to_update:
            print("Controller: No accounts to update.")
            return

        updated_count = 0
        failed_count = 0
        
        # Using ThreadPoolExecutor for concurrent scraping
        # Max 5 workers to avoid overwhelming the system or rate limits
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_account = {executor.submit(self._scrape_single_account_data, acc): acc for acc in accounts_to_update}
            for future in as_completed(future_to_account):
                original_account = future_to_account[future]
                name, link, platform, _, _ = original_account
                try:
                    scraped_data = future.result()
                    if scraped_data:
                        # Unpack scraped_data which should be (name, link, platform, followers, category)
                        # Ensure scraped_data contains all necessary fields for upsert_account
                        upsert_account(*scraped_data)
                        updated_count += 1
                        print(f"Controller: Updated {name} ({platform}) with {scraped_data[3]} followers.")
                    else:
                        # If scrape_single_account_data returns None or indicates failure, mark as failed
                        upsert_account(name, link, platform, 0, "failed")
                        failed_count += 1
                        print(f"Controller: Failed to scrape or update {name} ({platform}).")

                except Exception as e:
                    print(f"Controller: Error processing {name} ({link}): {e}", file=sys.stderr)
                    upsert_account(name, link, platform, 0, "failed") # Mark as failed in DB
                    failed_count += 1
        
        print(f"Controller: All accounts update finished. Updated: {updated_count}, Failed: {failed_count}.")
        self.ui.root.after(0, self.ui.refresh) # Refresh UI on main thread after all updates

    def update_selected(self, links_to_update):
        """
        Updates only the accounts specified by their links.
        This is called by the UI when 'Update Data' button is clicked.
        Includes platform validation for each selected link.
        """
        print(f"Controller: Initiating update for selected accounts: {links_to_update}...")
        if not links_to_update:
            print("Controller: No links provided for selected update.")
            return

        accounts_to_scrape = []
        all_current_accounts = fetch_all_accounts()
        
        for link in links_to_update:
            account = next((acc for acc in all_current_accounts if acc[1] == link), None)
            if account:
                name, current_link, current_platform, _, _ = account
                detected_platform = auto_detect_platform(current_link)

                # Validate platform consistency for update
                if detected_platform and detected_platform.lower() != current_platform.lower():
                    tk.messagebox.showwarning("Platform Mismatch", 
                                             f"Skipping update for '{name}' (Link: {current_link}). "
                                             f"Detected platform '{detected_platform}' does not match stored platform '{current_platform}'.")
                    print(f"Controller: Skipping update for {name} due to platform mismatch: Link detected as '{detected_platform}', stored as '{current_platform}'", file=sys.stderr)
                    # Mark as failed_platform in DB if it was previously valid, or just skip
                    upsert_account(name, current_link, current_platform, 0, "failed_platform")
                    continue # Skip this account for scraping
                
                # If the stored platform is not in supported scrapers, mark as failed_platform
                if current_platform.lower() not in self.scrapers:
                    tk.messagebox.showwarning("Unsupported Platform", 
                                             f"Skipping update for '{name}' (Link: {current_link}). "
                                             f"Stored platform '{current_platform}' is not supported for scraping.")
                    print(f"Controller: Skipping update for {name} due to unsupported stored platform: {current_platform}", file=sys.stderr)
                    upsert_account(name, current_link, current_platform, 0, "failed_platform")
                    continue # Skip this account for scraping

                accounts_to_scrape.append(account)
            else:
                print(f"Controller: Account with link {link} not found in database for selected update. Skipping.", file=sys.stderr)

        if not accounts_to_scrape:
            print("Controller: No valid accounts found for selected update after validation.")
            self.ui.root.after(0, self.ui.refresh) # Refresh UI even if no accounts to update
            return

        updated_count = 0
        failed_count = 0

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_account = {executor.submit(self._scrape_single_account_data, acc): acc for acc in accounts_to_scrape}
            for future in as_completed(future_to_account):
                original_account = future_to_account[future]
                name, link, platform, _, _ = original_account # Unpack for logging/error handling
                try:
                    scraped_data = future.result() # This will be (name, link, platform, followers, category) or None
                    if scraped_data:
                        upsert_account(*scraped_data)
                        updated_count += 1
                        print(f"Controller: Updated selected account {name} ({platform}) with {scraped_data[3]} followers.")
                    else:
                        # If scrape_single_account_data returns None, it means scraping failed
                        upsert_account(name, link, platform, 0, "failed") # Mark as failed
                        failed_count += 1
                        print(f"Controller: Failed to scrape or update selected account {name} ({platform}).")
                except Exception as e:
                    print(f"Controller: Error processing selected account {name} ({link}): {e}", file=sys.stderr)
                    upsert_account(name, link, platform, 0, "failed") # Mark as failed
                    failed_count += 1

        print(f"Controller: Selected accounts update finished. Updated: {updated_count}, Failed: {failed_count}.")
        self.ui.root.after(0, self.ui.refresh) # Refresh UI on main thread after selected updates

    def _scrape_single_account_data(self, account_data):
        """
        Helper method to scrape a single account and return its processed data.
        Designed to be run in a thread pool.
        Returns (name, link, platform, followers, category) or None on failure.
        This method assumes platform is already validated by the calling function.
        """
        name, link, platform, _, _ = account_data
            
        scraper = self.scrapers.get(platform)
        if scraper:
            try:
                followers = scraper.scrape(link)
                category = self._determine_category(followers)
                return (name, link, platform, followers, category)
            except Exception as e:
                print(f"Controller: Scraping failed for {link} (platform: {platform}): {e}", file=sys.stderr)
                return (name, link, platform, 0, "failed") # Return with failed status
        else:
            # This else block should ideally not be hit if initial validation is robust.
            print(f"Controller: Unexpected: Scraper not found for platform {platform} for link {link}. Marking as failed.", file=sys.stderr)
            return (name, link, platform, 0, "failed") # Fallback to generic failed

    def import_csv(self, file_path):
        """
        Imports accounts from a CSV file, adds them to the database,
        and initiates scraping for each imported account.
        """
        print(f"Controller: Importing CSV from {file_path}")
        imported_accounts_data = []
        try:
            with open(file_path, newline='', encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None) # Read header
                if header is None:
                    tk.messagebox.showwarning("Import CSV", "The CSV file is empty.")
                    return

                # Determine column indices from header, case-insensitive
                header_map = {h.strip().lower(): i for i, h in enumerate(header)}
                name_idx = header_map.get("name")
                link_idx = header_map.get("link")
                platform_idx = header_map.get("platform")

                if name_idx is None or link_idx is None:
                    tk.messagebox.showerror("Import CSV Error", "CSV must contain 'Name' and 'Link' columns.")
                    return

                for i, row in enumerate(reader):
                    try:
                        name = row[name_idx].strip()
                        link = row[link_idx].strip()
                        
                        platform = None
                        if platform_idx is not None and len(row) > platform_idx:
                            platform = row[platform_idx].strip().lower()

                        if not name or not link:
                            print(f"Controller: Skipping row {i+2}: Name or Link is empty. Row: {row}")
                            continue

                        # Validate platform for imported accounts
                        if platform not in self.scrapers: # If platform from CSV is not directly supported
                            auto_detected_platform = auto_detect_platform(link)
                            if auto_detected_platform in self.scrapers: # If auto-detected is supported
                                platform = auto_detected_platform
                            else: # Neither provided nor auto-detected is supported
                                print(f"Controller: Skipping row {i+2}: Could not determine supported platform for link '{link}'. Row: {row}")
                                upsert_account(name, link, "unknown", 0, "failed_platform") # Add as unsupported
                                continue
                        
                        # Add to a temporary list. Actual scraping will happen in a pool.
                        imported_accounts_data.append((name, link, platform))
                        # Immediately add to DB with pending status to show in UI
                        upsert_account(name, link, platform, 0, "pending")
                        print(f"Controller: Queued for import: {name} ({link}) on {platform}")

                    except IndexError as ie:
                        print(f"Controller: Row {i+2} is malformed or has too few columns: {row}. Error: {ie}", file=sys.stderr)
                        continue # Skip malformed rows
                    except Exception as row_e:
                        print(f"Controller: Error processing row {i+2}: {row_e}. Row: {row}", file=sys.stderr)
                        continue

            self.ui.refresh() # Refresh UI to show all newly added "pending" accounts

            if not imported_accounts_data:
                tk.messagebox.showinfo("Import CSV", "No valid accounts found to import from the CSV.")
                return

            # Now, initiate scraping for all imported accounts concurrently
            print(f"Controller: Starting concurrent scraping for {len(imported_accounts_data)} imported accounts...")
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                # Submit scraping tasks for each imported account
                future_to_account = {executor.submit(self._scrape_single_account_data, (name, link, platform, 0, "pending")): (name, link, platform) for name, link, platform in imported_accounts_data}
                
                for future in as_completed(future_to_account):
                    original_name, original_link, original_platform = future_to_account[future]
                    try:
                        scraped_result = future.result() # This will be (name, link, platform, followers, category) or (name, link, platform, 0, "failed")
                        if scraped_result:
                            upsert_account(*scraped_result) # Update DB with scraped data
                            print(f"Controller: Finished import scrape for {original_name} ({original_platform}).")
                        else:
                            print(f"Controller: Scraping for imported account {original_name} ({original_link}) failed.")
                    except Exception as e:
                        print(f"Controller: Error during concurrent scrape for imported account {original_name} ({original_link}): {e}", file=sys.stderr)
                        upsert_account(original_name, original_link, original_platform, 0, "failed") # Mark as failed

            tk.messagebox.showinfo("Import Complete", f"CSV import and scraping process finished.")

        except FileNotFoundError:
            tk.messagebox.showerror("Import CSV Error", "File not found.")
        except Exception as e:
            print(f"Controller: General error during CSV import: {e}", file=sys.stderr)
            tk.messagebox.showerror("Import CSV Error", f"An error occurred during CSV import: {e}")
        finally:
            self.ui.root.after(0, self.ui.refresh) # Ensure UI refreshes after all operations

    def export_csv(self):
        """
        Exports all current accounts in the database to a CSV file.
        """
        print("Controller: Exporting data to CSV...")
        try:
            export_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                     filetypes=[("CSV files", "*.csv")],
                                                     title="Export Accounts")
            if export_path:
                export_csv_to_file(export_path)
                tk.messagebox.showinfo("Export Complete", f"Data exported to {export_path}")
                self.ui.refresh() # Refresh UI (though not strictly necessary after export)
            else:
                print("Controller: CSV export cancelled.")
        except Exception as e:
            tk.messagebox.showerror("Export Error", f"Error exporting CSV file: {e}")
            print(f"Error exporting CSV file: {e}", file=sys.stderr)

    def fetch_all(self):
        """
        Fetches all account records from the database.
        """
        return fetch_all_accounts()

    def sort_by(self, tree, col):
        """
        Sorts the Treeview table by the specified column.
        Handles both numeric and string sorting.
        """
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            # Attempt to sort as int, fallback to string sort
            data.sort(key=lambda t: int(t[0]))
        except ValueError:
            data.sort(key=lambda t: t[0].lower())
        
        # Reorder the Treeview items based on the sorted data
        for index, (_, k) in enumerate(data):
            tree.move(k, "", index)

def main():
    root = tk.Tk()
    app_controller = Controller(root)
    # The AppUI object already has a reference to the controller passed during its initialization.
    # No need for app_controller...

    root.mainloop()

if __name__ == '__main__':
    # Ensure threading is imported for Controller's add_account
    import threading 
    main()
