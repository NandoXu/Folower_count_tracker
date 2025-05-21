import sqlite3
import csv
import tkinter.filedialog

DB_PATH = "accounts.db"

def init_db():
    """
    Initialize the SQLite database and create the accounts table if it doesn't exist.
    The table has the following columns:
      - id: Unique primary key.
      - name: The account name.
      - link: The account link (must be unique).
      - platform: The social media platform (e.g., instagram, tiktok, twitter).
      - followers: The number of followers.
      - category: A string defining the account category (e.g., "micro", "macro", or "pending").
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            link TEXT NOT NULL UNIQUE,
            platform TEXT NOT NULL,
            followers INTEGER NOT NULL,
            category TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def upsert_account(name, link, platform, followers, category):
    """
    Insert a new account record or, if the record already exists (based on the unique link),
    update the follower count and category.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO accounts (name, link, platform, followers, category)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(link) DO UPDATE SET
            followers = excluded.followers,
            category = excluded.category
    """, (name, link, platform, followers, category))
    conn.commit()
    conn.close()

def delete_account(link):
    """
    Delete an account record from the database where the link matches the given link.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM accounts WHERE link = ?", (link,))
    conn.commit()
    conn.close()

def fetch_all_accounts():
    """
    Fetch all account records from the database.
    Returns:
      A list of tuples, each tuple in the form:
         (name, link, platform, followers, category)
    """
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT name, link, platform, followers, category FROM accounts").fetchall()
    conn.close()
    return rows

def export_csv(file_path=None):
    """
    Export all account data to a CSV file.
    If file_path is None, a file dialog will open to allow the user to choose a save path.
    The CSV columns are: Name, Link, Platform, Followers, Category.
    """
    if file_path is None:
        file_path = tkinter.filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Choose filename for CSV export"
        )
        # If the user canceled the dialog, exit the function.
        if not file_path:
            return

    accounts = fetch_all_accounts()
    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Name", "Link", "Platform", "Followers", "Category"])
        for row in accounts:
            writer.writerow(row)

def auto_detect_platform(link):
    """
    A helper function to auto-detect the platform based on the link.
    This function uses a simple heuristic:
      - If "instagram.com" is in the link, it's "instagram".
      - If "tiktok.com" is in the link, it's "tiktok".
      - If "twitter.com" or "x.com" is in the link, it's "twitter".
      - Otherwise, it returns "unknown".
    """
    link_lower = link.lower()
    if "instagram.com" in link_lower:
        return "instagram"
    elif "tiktok.com" in link_lower:
        return "tiktok"
    elif "twitter.com" in link_lower or "x.com" in link_lower:
        return "twitter"
    else:
        return "unknown"

def import_csv(file_path=None):
    """
    Import account data from a CSV file.
    
    The CSV file is expected to have at least the Name and Link columns.
    For each row, the platform is auto-detected from the link, and the record
    is inserted (or updated) into the database with a default followers count of 0 
    and a category of "pending". The rest of the data will be updated later via scraping.
    If file_path is None, a file dialog will open for the user to select a CSV file.
    """
    if file_path is None:
        file_path = tkinter.filedialog.askopenfilename(
            title="Select CSV file to import",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not file_path:
            return

    with open(file_path, "r", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader, None)
        # Optionally, you can check header titles here.
        for row in reader:
            if len(row) < 2:
                continue  # Skip rows that don't have at least Name and Link.
            name = row[0].strip()
            link = row[1].strip()
            if not (name and link):
                continue
            platform = auto_detect_platform(link)
            # Set default values: followers 0 and category "pending".
            upsert_account(name, link, platform, 0, "pending")
