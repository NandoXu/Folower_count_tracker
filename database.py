# database.py
import sqlite3
import csv
import tkinter.filedialog # Only if you use tkinter for file dialog, otherwise remove this import
from typing import List, Tuple

DB_PATH = "accounts.db"

def init_db():
    # ... (existing init_db function) ...
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
            followers=excluded.followers,
            category=excluded.category
    """, (name, link, platform, followers, category))
    conn.commit()
    conn.close()

def bulk_upsert_accounts(accounts_data: List[Tuple[str, str, str, int, str]]):
    """
    Bulk insert or update multiple account records.
    accounts_data is a list of tuples: (name, link, platform, followers, category)
    """
    conn = sqlite3.connect(DB_PATH)
    conn.executemany("""
        INSERT INTO accounts (name, link, platform, followers, category)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(link) DO UPDATE SET
            followers=excluded.followers,
            category=excluded.category
    """, accounts_data)
    conn.commit()
    conn.close()


def delete_account(link):
    # ... (existing delete_account function) ...
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM accounts WHERE link=?", (link,))
    conn.commit()
    conn.close()


def fetch_all_accounts():
    # ... (existing fetch_all_accounts function) ...
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT name, link, platform, followers, category FROM accounts")
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def export_csv_to_file(file_path):
    # ... (existing export_csv function, potentially renamed to avoid conflict if `import_csv` uses a global function) ...
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute("SELECT name, link, platform, followers, category FROM accounts")
    rows = cursor.fetchall()
    conn.close()

    with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Name", "Link", "Platform", "Followers", "Category"])
        writer.writerows(rows)

def auto_detect_platform(link):
    # ... (existing auto_detect_platform function) ...
    link_lower = link.lower()
    if "instagram.com" in link_lower:
        return "instagram"
    elif "tiktok.com" in link_lower:
        return "tiktok"
    elif "x.com" in link_lower or "twitter.com" in link_lower:
        return "twitter"
    else:
        return "unknown"

# Note: The import_csv function in database.py seems to be a placeholder
# and the actual import logic is in main.py. Keep import_csv in main.py
# but make sure it uses bulk_upsert_accounts.