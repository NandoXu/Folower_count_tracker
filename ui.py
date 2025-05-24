import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import base64
import io
from PIL import Image, ImageTk # PIL (Pillow) is required for image handling
import os
import sys
import csv # Ensure csv is imported for DummyController
import time # Import time for sleep in dummy controller

# For concurrent processing of the queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# ------------------ Helper Functions ------------------
def resource_path(relative_path):
    """
    Get absolute path to a resource; works for both development and frozen executables.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_icon():
    """
    Load a PhotoImage for the window icon.
    Use base64 data from icon_base64 if available (and not equal to "base placeholder");
    otherwise, fall back to loading 'important.ico'.
    """
    try:
        # Check if icon_base64 contains actual data or is a placeholder
        if icon_base64.strip() and icon_base64.strip() != "base placeholder":
            print("Using base64 icon. Length:", len(icon_base64.strip()))
            data = base64.b64decode(icon_base64)
            img = Image.open(io.BytesIO(data))
            return ImageTk.PhotoImage(img)
        else:
            print("No valid base64 icon provided; loading from file fallback.")
            icon_path = resource_path("important.ico")
            print("Fallback icon path:", icon_path)
            img = Image.open(icon_path)
            return ImageTk.PhotoImage(img)
    except Exception as e:
        print("Error loading icon:", e)
        return None

# ------------------ Base64 Data (Replaced with placeholders as requested) ------------------
icon_base64 = "base placeholder" # For title bar and taskbar
logo_base64 = "base placeholder" # For the loading overlay


# ------------------- UI Class -------------------
class AppUI:
    """
    Desktop UI with a two-column layout.

    LEFT PANEL:
      - Contains input fields for Name, Link, and Platform.
      - Primary buttons: "Add Account" and "Delete".
      - Secondary buttons: "Update Selected Data", "Import CSV", and "Export CSV".

    RIGHT PANEL:
      - Contains a Treeview table for displaying data.

    OVERLAY:
      - Displayed during long operations (includes a logo and a spinner).
    """
    def __init__(self, root, controller):
        self.root = root
        self.ctrl = controller
        self.overlay = None
        self.spinner_canvas = None
        self.spinner_arc = None
        self.spinner_angle = 0
        self.icon_img = None    # Window icon image reference
        self.logo_img = None    # Overlay logo image reference (kept as instance var to prevent GC)

        root.title("Social Media Tracker")
        root.configure(bg="white")
        root.geometry("1000x600")
        root.minsize(1000, 600)

        # --- Set window icon using base64 or fallback to ICO ---
        self.icon_img = load_icon()
        if self.icon_img:
            root.iconphoto(True, self.icon_img)
        else:
            print("No icon loaded; the window icon may be missing.")
            messagebox.showwarning("Icon Warning", "Could not load window icon. It might be missing or corrupted.")


        # ------------------ Styling ------------------
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure("TFrame", background="white")
        style.configure("TLabel", background="white", foreground="#333", font=("Helvetica", 11))
        style.configure("TEntry", fieldbackground="white", relief="flat", padding=6)
        style.configure("TButton", background="#C6E7FF", foreground="#333",
                                 relief="flat", borderwidth=0, font=("Helvetica", 11), padding=6)
        style.map("TButton", background=[("active", "#B0D4FF")])
        style.configure("Treeview", background="white", fieldbackground="white", font=("Helvetica", 10))
        style.configure("Treeview.Heading", background="#C6E7FF", foreground="#333", font=("Helvetica", 11, "bold"))
        # Moved to after self.tree is defined: style.tag_configure("failed", background="#FFCCCC") # Configure tag for failed rows

        # ------------------ Layout ------------------
        root.grid_columnconfigure(0, weight=0)
        root.grid_columnconfigure(1, weight=1)
        root.grid_rowconfigure(0, weight=1)

        # LEFT PANEL (inputs and buttons)
        lf = ttk.Frame(root, padding=10)
        lf.grid(row=0, column=0, sticky="nsew")
        lf.grid_columnconfigure(1, weight=1)
        # Configure rows for input fields and buttons
        lf.grid_rowconfigure(0, weight=0) # Name
        lf.grid_rowconfigure(1, weight=0) # Link
        lf.grid_rowconfigure(2, weight=0) # Platform
        lf.grid_rowconfigure(3, weight=0) # Add Account
        lf.grid_rowconfigure(4, weight=0) # Delete
        lf.grid_rowconfigure(5, weight=1) # Spacer
        lf.grid_rowconfigure(6, weight=0) # Update Data
        lf.grid_rowconfigure(7, weight=0) # Import CSV
        lf.grid_rowconfigure(8, weight=0) # Export CSV

        ttk.Label(lf, text="Name:").grid(row=0, column=0, sticky="w", pady=5)
        ttk.Label(lf, text="Link:").grid(row=1, column=0, sticky="w", pady=5)
        ttk.Label(lf, text="Platform:").grid(row=2, column=0, sticky="w", pady=5)
        self.name_var = tk.StringVar()
        self.link_var = tk.StringVar()
        self.platform_var = tk.StringVar()
        ttk.Entry(lf, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Entry(lf, textvariable=self.link_var).grid(row=1, column=1, sticky="ew", pady=5)
        cb = ttk.Combobox(lf, textvariable=self.platform_var,
                                  values=["instagram", "tiktok", "twitter"],
                                  state="readonly")
        cb.grid(row=2, column=1, sticky="ew", pady=5)
        cb.current(0) # Set initial selection

        ttk.Button(lf, text="Add Account", command=self.on_add).grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(lf, text="Delete", command=self.on_delete).grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

        # Spacer to push bottom buttons down
        lf.grid_rowconfigure(5, weight=1)

        # Renamed button and updated command to handle selected data only
        ttk.Button(lf, text="Update Data", command=self.on_update_selected).grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(lf, text="Import CSV", command=self.on_import_csv).grid(row=7, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Button(lf, text="Export CSV", command=self.ctrl.export_csv).grid(row=8, column=0, columnspan=2, sticky="ew", pady=5)

        # RIGHT PANEL (Treeview)
        rf = ttk.Frame(root, padding=10)
        rf.grid(row=0, column=1, sticky="nsew")
        rf.grid_columnconfigure(0, weight=1)
        rf.grid_rowconfigure(0, weight=1)
        cols = ("Name", "Link", "Platform", "Followers", "Category")
        self.tree = ttk.Treeview(rf, columns=cols, show="headings", selectmode="extended")
        for c in cols:
            self.tree.heading(c, text=c, command=lambda _c=c: self.ctrl.sort_by(self.tree, _c))
            self.tree.column(c, width=120, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        ttk.Scrollbar(rf, orient="vertical", command=self.tree.yview).grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=lambda f, s: None) # Disable default scrollbar behavior

        # --- Configure the "failed" tag on the Treeview itself ---
        self.tree.tag_configure("failed", background="#FFCCCC")

        # Bind right-click to show context menu
        self.tree.bind("<Button-3>", self._show_context_menu)

        self.refresh()

    def _spin(self):
        """Animates the spinner on the overlay."""
        self.spinner_angle = (self.spinner_angle + 5) % 360
        self.spinner_canvas.itemconfig(self.spinner_arc, start=self.spinner_angle)
        self.spinner_canvas.after(33, self._spin)

    def show_overlay(self, text="Loading..."):
        """Displays a full-screen overlay with a message, logo, and spinner."""
        if self.overlay:
            return # Overlay is already visible

        self.overlay = tk.Frame(self.root, bg="#D3D3D3")
        self.overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.overlay.lift() # Bring overlay to top

        # Create a semi-transparent background for the overlay
        canvas_bg = tk.Canvas(self.overlay, bg="#D3D3D3", highlightthickness=0)
        canvas_bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.root.update_idletasks() # Ensure window dimensions are updated
        w, h = self.root.winfo_width(), self.root.winfo_height()
        canvas_bg.create_rectangle(0, 0, w, h, fill="#D3D3D3", outline="", stipple="gray75")

        # Container for message, logo, and spinner
        container = tk.Frame(self.overlay, bg="#D3D3D3")
        container.place(relx=0.5, rely=0.5, anchor="center")

        lbl = tk.Label(container, text=text, fg="#333", bg="#D3D3D3", font=("Helvetica", 16))
        lbl.pack(pady=(0, 10))

        # Load and display the overlay logo
        try:
            # Check if logo_base64 contains actual data or is a placeholder
            if logo_base64.strip() and logo_base64.strip() != "base placeholder":
                logo_data = base64.b64decode(logo_base64)
                logo_img = Image.open(io.BytesIO(logo_data))
                self.logo_img = ImageTk.PhotoImage(logo_img) # Keep reference to prevent GC
                logo_lbl = tk.Label(container, image=self.logo_img, bg="#D3D3D3")
                logo_lbl.pack(pady=(0, 10))
            else:
                print("No valid base64 overlay logo provided.")
        except Exception as e:
            print("Overlay logo decode error:", e)
            messagebox.showwarning("Logo Warning", "Could not load overlay logo. Ensure the base64 string is valid.")

        # Spinner setup
        size = 80
        self.spinner_canvas = tk.Canvas(container, width=size, height=size, bg="#D3D3D3", highlightthickness=0)
        self.spinner_canvas.pack()
        pad = 10
        self.spinner_arc = self.spinner_canvas.create_arc(
            pad, pad, size - pad, size - pad,
            start=0, extent=270,
            style="arc", outline="#C6E7FF", width=6
        )
        self._spin() # Start the spinner animation

    def hide_overlay(self):
        """Hides the full-screen overlay."""
        if not self.overlay:
            return
        self.overlay.destroy()
        self.overlay = None
        self.spinner_canvas = None
        self.spinner_arc = None

    def clear_inputs(self):
        """Clears the input fields."""
        self.name_var.set("")
        self.link_var.set("")
        self.platform_var.set("instagram") # Reset platform to default

    def on_add(self):
        """
        Handles the 'Add Account' button click.
        The overlay will remain visible until the newly added account's data
        has been fully scraped and is no longer in a "pending" state.
        """
        name = self.name_var.get().strip()
        link = self.link_var.get().strip()
        plat = self.platform_var.get().strip()

        if not (name and link and plat):
            messagebox.showerror("Input Error", "Please fill all fields.")
            return

        self.show_overlay("Adding and Scraping...") # More descriptive message

        def task():
            try:
                # Add the account to the controller. It will be initially "pending".
                self.ctrl.add_account(name, link, plat)

                # Now, wait for this specific account to be scraped
                scraped_status = "pending"
                while scraped_status == "pending":
                    found = False
                    for rec_name, rec_link, rec_platform, rec_followers, rec_category in self.ctrl.fetch_all():
                        if rec_link == link: # Found the account we just added
                            scraped_status = rec_category
                            found = True
                            break
                    if not found: # Should not happen if add_account worked, but a safeguard
                        print(f"Warning: Added account with link {link} not found in data after add.")
                        break # Exit loop if account somehow disappears
                    if scraped_status == "pending":
                        time.sleep(0.1) # Wait a bit before checking again

            except Exception as ex:
                error_msg = str(ex)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Add Error", msg))
            finally:
                self.root.after(0, self.hide_overlay)
                self.root.after(0, self.refresh)
                self.root.after(0, self.clear_inputs)

        threading.Thread(target=task, daemon=True).start()

    def on_update_selected(self):
        """Handles the 'Update Selected Data' button click or context menu option."""
        selections = list(self.tree.selection())
        if not selections:
            messagebox.showerror("Selection Error", "Select one or more items to update.")
            return

        links_to_update = []
        for sel in selections:
            try:
                values = self.tree.item(sel).get("values", [])
                if len(values) >= 2: # Ensure link column exists (link is at index 1)
                    links_to_update.append(values[1])
            except Exception as ex:
                print("Error retrieving tree item for update:", ex) # Log error but continue

        if not links_to_update:
            messagebox.showwarning("Update Warning", "No valid items selected for update.")
            return

        self.show_overlay("Updating Selected...")
        def task():
            try:
                # Call the new controller method to update only selected links
                self.ctrl.update_selected(links_to_update)
            except Exception as ex:
                error_msg = str(ex)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Update Error", msg))
            finally:
                self.root.after(0, self.hide_overlay)
                self.root.after(0, self.refresh)
        threading.Thread(target=task, daemon=True).start()

    def on_delete(self):
        """Handles the 'Delete' button click."""
        selections = list(self.tree.selection())
        if not selections:
            messagebox.showerror("Selection Error", "Select one or more items.")
            return
        links_to_delete = []
        for sel in selections:
            try:
                values = self.tree.item(sel).get("values", [])
                if len(values) >= 2: # Ensure link column exists
                    links_to_delete.append(values[1])
            except Exception as ex:
                print("Error retrieving tree item:", ex) # Log error but continue

        if not links_to_delete: # If no valid links were found to delete
            messagebox.showwarning("Delete Warning", "No valid items selected for deletion.")
            return

        for link in links_to_delete:
            try:
                self.ctrl.delete_account(link)
            except Exception as e:
                messagebox.showerror("Delete Error", f"Error deleting {link}: {e}")
        self.refresh() # Refresh UI after deletion

    def on_import_csv(self):
        """Handles the 'Import CSV' button click."""
        path = filedialog.askopenfilename(title="Select CSV", filetypes=[("CSV files", "*.csv")])
        if path:
            self.show_overlay("Importing and Scraping...")
            def task():
                try:
                    self.ctrl.import_csv(path)
                except Exception as ex: # Changed 'e' to 'ex'
                    error_msg = str(ex)
                    self.root.after(0, lambda msg=error_msg: messagebox.showerror("Import CSV Error", msg))
                finally:
                    self.root.after(0, self.hide_overlay)
                    self.root.after(0, self.refresh)
            threading.Thread(target=task, daemon=True).start()
        else:
            self.refresh() # Refresh even if no file selected, to clear any previous state

    def refresh(self):
        """Refreshes the data displayed in the Treeview."""
        # Clear existing entries
        for i in self.tree.get_children():
            self.tree.delete(i)
        # Fetch and insert new data
        for row in self.ctrl.fetch_all():
            tags = ()
            # Apply 'failed' tag for red background, including for platform errors
            if len(row) > 4 and (str(row[4]).lower() == "failed" or str(row[4]).lower() == "failed_platform"):
                tags = ("failed",)
            self.tree.insert("", "end", values=row, tags=tags)
        # The tag configuration is done once in __init__ now, but can be here too for dynamic changes.
        # self.tree.tag_configure("failed", background="#FFCCCC")

    def _show_context_menu(self, event):
        """Displays a context menu on right-click for the Treeview."""
        menu = tk.Menu(self.tree, tearoff=0)
        menu.add_command(label="Select All", command=self._select_all_items)
        ## FIX: Indentation corrected here. The 'try' block was incorrectly indented.
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release() # Release the grab when the menu is dismissed

    def _select_all_items(self):
        """Selects all items in the Treeview."""
        for item in self.tree.get_children():
            self.tree.selection_add(item)


# ------------------- Dummy Controller -------------------
# This is a placeholder controller for UI testing.
# In a real application, this would be your main.py's Controller class.
class DummyController:
    def __init__(self):
        self.data = []  # Each record: (name, link, platform, followers, category)
        self.scrape_queue = []
        self.scrape_thread_started = False
        self.on_data_update = lambda: None # Callback for UI refresh

    def add_account(self, name, link, platform):
        # Simulate adding an account with initial dummy data
        self.data.append((name, link, platform, 0, "pending"))
        self.scrape_queue.append((name, link, platform)) # Add to scrape queue immediately
        print(f"Dummy: Added account {name} ({platform})")
        if not self.scrape_thread_started:
            threading.Thread(target=self.continuous_scraping, daemon=True).start()
            self.scrape_thread_started = True

    def delete_account(self, link):
        # Simulate deleting an account
        original_len = len(self.data)
        self.data = [r for r in self.data if r[1] != link]
        print(f"Dummy: Deleted account with link {link}. {original_len - len(self.data)} items removed.")

    def update_selected(self, links_to_update):
        """Simulates updating only selected accounts."""
        print(f"Dummy: Updating selected accounts: {links_to_update}...")
        updated_data = []
        # Create a set for faster lookup of links to update
        links_set = set(links_to_update)

        for rec in self.data:
            if rec[1] in links_set: # If this record's link is in the selected list
                # Simulate re-scraping the account
                new_rec = self.scrape_account((rec[0], rec[1], rec[2]))
                updated_data.append(new_rec)
            else:
                updated_data.append(rec) # Keep existing record as is
        self.data = updated_data
        print("Dummy: Selected accounts updated.")

    def import_csv(self, path):
        """
        Dummy CSV import: reads name, link, and optionally platform.
        Mimics the main.py Controller's logic for platform determination.
        """
        print(f"Dummy: Importing CSV from {path}")
        try:
            with open(path, newline='', encoding="utf-8") as f:
                reader = csv.reader(f)
                # Skip header row if it exists (assuming your CSV has one)
                try:
                    header = next(reader)
                    # You might want to validate header here if needed
                except StopIteration:
                    # CSV was empty or only had header
                    print("Dummy: CSV file is empty or only contains header.")
                    return

                for i, row in enumerate(reader):
                    new_row = [cell.strip() for cell in row]

                    if len(new_row) < 2:
                        print(f"Dummy: Skipping row {i+1}: Not enough columns: {new_row}")
                        continue

                    name = new_row[0]
                    link = new_row[1]
                    platform = "unknown" # Default platform if not found or inferred

                    if len(new_row) >= 3:
                        platform = new_row[2].lower()
                    else:
                        # Attempt to infer platform from the link
                        if "instagram.com" in link:
                            platform = "instagram"
                        elif "tiktok.com" in link:
                            platform = "tiktok"
                        elif "x.com" in link or "twitter.com" in link:
                            platform = "twitter"
                        else:
                            print(f"Dummy: Could not determine platform for link '{link}' (row {i+1})")
                            continue # Skip if platform cannot be determined

                    # In a real scenario, you'd check if the platform is supported by a scraper.
                    # For this dummy, we'll just accept it or warn if it's 'unknown'.
                    if platform == "unknown":
                        print(f"Dummy: Warning: Platform for '{name}' could not be determined. Using 'unknown'.")

                    print(f"Dummy: Imported row {i+1}: {new_row} -> platform '{platform}'")
                    self.scrape_queue.append((name, link, platform))

        except Exception as e:
            print(f"Dummy: Error importing CSV file: {e}")
            # In a real app, you might re-raise or handle this more gracefully.

        if not self.scrape_thread_started:
            # Start a background thread to simulate scraping imported accounts
            threading.Thread(target=self.continuous_scraping, daemon=True).start()
            self.scrape_thread_started = True
        print("Dummy: CSV import finished. Scraping initiated.")

    def scrape_account(self, account):
        """Simulates scraping a single account."""
        name, link, platform = account
        time.sleep(0.5)  # Simulate network delay

        # Define allowed platforms for scraping
        allowed_platforms = ["instagram", "tiktok", "twitter"]

        # Simulate success or failure based on link content
        if "fail" in link.lower():
            return (name, link, platform, 0, "failed")
        # Check if the platform is valid
        elif platform.lower() not in allowed_platforms:
            print(f"Dummy: Skipping scrape for {name} on unsupported platform: {platform}")
            return (name, link, platform, 0, "failed_platform") # New category for clarity
        else:
            # Return some dummy follower count
            follower_count = 12345 + len(name) * 100

            # Determine category based on follower count
            if follower_count >= 50000: # Example threshold for 'macro'
                category = "macro"
            else:
                category = "micro"

            return (name, link, platform, follower_count, category)

    def continuous_scraping(self):
        """Continuously processes accounts in the scrape_queue."""
        while True:
            if self.scrape_queue:
                account = self.scrape_queue.pop(0)
                result = self.scrape_account(account)

                updated = False
                for i, rec in enumerate(self.data):
                    if rec[1] == result[1]: # Update existing entry if link matches
                        self.data[i] = result
                        updated = True
                        break
                if not updated: # Add as new if not found
                    self.data.append(result)

                self.on_data_update() # Notify UI to refresh
            else:
                time.sleep(1) # Wait if queue is empty

    def export_csv(self):
        """Dummy CSV export: saves current data to a CSV file."""
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV files", "*.csv")],
                                             title="Export CSV")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(("Name", "Link", "Platform", "Followers", "Category"))
                writer.writerows(self.data)
            messagebox.showinfo("Export Complete", f"Data exported to {path}")
            print(f"Dummy: Data exported to {path}")

    def fetch_all(self):
        """Returns all currently stored dummy accounts."""
        return self.data

    def sort_by(self, tree, col):
        """Dummy sort function for the Treeview."""
        print(f"Dummy: Sorting by column: {col}")
        data = [(tree.set(k, col), k) for k in tree.get_children("")]
        try:
            # Attempt to sort as int, fallback to string sort
            data.sort(key=lambda t: int(t[0]))
        except ValueError:
            data.sort(key=lambda t: t[0].lower())
        for index, (_, k) in enumerate(data):
            tree.move(k, "", index)

# ---------------------- Main ----------------------
if __name__ == '__main__':
    root = tk.Tk()
    controller = DummyController() # Use the DummyController for standalone UI testing
    app = AppUI(root, controller)
    controller.on_data_update = lambda: root.after(0, app.refresh) # Link dummy controller updates to UI refresh
    root.mainloop()
