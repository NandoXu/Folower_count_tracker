import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import base64
import io
from PIL import Image, ImageTk # PIL (Pillow) is required for image handling
import os
import sys
import csv # Ensure csv is imported for DummyController

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

# ------------------ Base64 Data ------------------
# Replace the following placeholders with your actual base64-encoded data when ready.
icon_base64 = """AAABAAEAICAAAAEAIACoEAAAFgAAACgAAAAgAAAAQAAAAAEAIAAAAAAAABAAABILAAASCwAAAAAAAAAAAABEZyb/RGYk/0RmJf9EZiX/RGYl/0RmJf9EaCj/RWws/0Z1Nv9Fbi7/RGUk/0NgHv9DXhz/Q2Ef/0RjIf9EZCL/RGIh/0NfHf9DXRv/Q2Ae/0RlJP9EZiX/RGYl/0RnJ/9Fby//RWoq/0RmJf9EZiX/RGYl/0RlJP9EZiX/RGUk/0RmJf9EZiX/RGYl/0RmJf9EZiX/RW8v/0d6Pf9Gdjj/RXEy/0RmJf9DYSD/RGUk/0VtLf9FcDD/RXAx/0VwMf9Fbi7/RWws/0VpKf9EZCL/Q2Ef/0RlJP9EZyb/RnIz/0d9QP9HeTz/RW4v/0RnJv9EZiT/RGYl/0RmJf9EZiX/RGYl/0RmJf9EZST/RGgn/0ZyM/9HfD7/R31A/0ZyM/9EZiX/RGcm/0VtLf9GcTH/RnQ2/0Z3OP9Gdzn/Rnc4/0Z1N/9FcTL/RXEx/0VvMP9Fair/RGMi/0RkI/9GczT/R35B/0d9QP9HfD7/RnIz/0RnJ/9EZiX/RGYl/0RmJf9EZiX/RGYl/0RnJv9GdDb/R30//0d9QP9Hez3/RGgo/0RpKP9FcDH/RXAx/0ZxMv9GdDX/RnY3/0ZzNf9GcjP/RnM0/0VxMf9FcDH/RnEx/0VwMf9FbS3/RGQj/0RpKP9Gdzn/R31A/0d9P/9HfUD/RnU2/0RnJ/9EZiX/RGUk/0RmJf9EZyb/RnM0/0d9P/9HfT//R35A/0VuLv9EZyf/RnQ2/0ZyM/9GcTL/RnY3/0Z1Nv9FcDH/RWsr/0VqKf9FbCz/RW8v/0VxMf9FcTH/RXAx/0ZxMv9Fbi//Q14c/0VuL/9HfUD/R30//0d9P/9HfT//RnM0/0RnJv9EZiX/RGYl/0VwMf9HfD//R31A/0d8Pv9GdDX/RGcm/0ZzNf9Gdzn/RnY4/0ZzNP9GczT/RnIz/0VxMv9GcTL/RXEx/0VwMP9Fbi//RW4u/0VvMP9FcDH/RnEy/0Z0Nf9EZib/RGMi/0VwMf9HfT//R30//0d9P/9HfD//RXAw/0RmJf9Fayr/R3o8/0d9P/9HfD//R3w//0RkI/9EaSj/Rng5/0Z3OP9Gdjj/RXAw/0RkIv9EZyb/RWsr/0VsLf9Fayv/RWsq/0RpKP9EYyH/RWoq/0VwMf9FcDH/RnM0/0VtLf9DXRr/RWoq/0d9QP9HfT//R30//0d9QP9Hejz/RWoq/0Z2N/9HfT//R30//0d9P/9Hez3/RGUk/0ZxMf9Gdzn/Rnc4/0Z3OP9GczT/RWoq/0VqKv9Fbi//RXAw/0VuLv9FbS3/RW4u/0VrK/9FcDH/RnM0/0ZyM/9FcTL/RW8w/0RiIf9EZyf/R3w//0d9P/9HfT//R3w//0d9P/9GdDb/R30//0d9QP9HfT//R30//0Z0Nv9Fayv/RnQ2/0Z3Of9Gdzn/Rnc5/0Z3Of9Gdjf/RnU2/0ZzNf9GcjP/RXEy/0ZxMv9GdDX/RnY3/0Z3Of9Gdzn/RnY4/0ZyM/9FcTH/RGko/0RjIv9GcjP/R30//0d9P/9HfT//R30//0d8P/9HfUD/R30//0d9QP9HeTv/RnIz/0VuLv9GdDX/Rnc5/0Z3Of9Gdzn/Rnc5/0Z3Of9Gdjj/RnIz/0ZyM/9FcTH/RW4v/0VvMP9Gdjf/Rnc5/0Z4Of9Gdzn/RnY4/0ZyNP9Fayr/RGMh/0RpKP9GeTv/R31A/0d9P/9HfT//R31A/0d9QP9HfT//R3w//0Z0Nf9FbCz/RWsr/0Z2N/9Gdzn/RnU2/0ZyM/9FcTL/RnQ1/0VwMf9Fayv/RGYl/0VqKv9EZCP/RWoq/0Z0Nf9GdTb/RnEy/0VvMP9GczT/RnU2/0VtLf9DYR//RGUk/0VxMf9HfT//R3w//0d9P/9HfUD/R30//0d9QP9Hejz/RnEy/0RoJ/9FbzD/Rnc5/0VvL/9DYB7/Q1sY/0NaF/9DYB7/RWsr/0ZyM/9FcDH/RnM1/0VvL/9FcDH/RWss/0NfHf9CWRb/QlkW/0NgH/9Fbi7/RW8v/0NgHv9EZCP/RWoq/0d7Pv9HfT//R30//0d+Qf9HfUD/R31A/0d4Ov9GcjL/RGop/0ZyM/9FcTH/QlsY/0JXFP9CWRb/QlkW/0JXE/9DXBr/RW4u/0Z3Of9Hejz/RnY4/0VsLP9CWRb/QlYS/0JZFf9CWRX/QlcU/0NfHf9FbCz/RGIh/0RjIv9EaCj/R3o8/0d9P/9HfD//R35B/0d9QP9HfUD/Rng6/0VrK/9Fair/RnQ1/0RlJP9CVhP/QloX/0JZFv9DWRf/QloX/0JYFf9EZCT/RnQ1/0d6PP9GdDX/Q2Af/0JVEv9CWRb/QlkX/0NaF/9DWhf/QlkW/0RoJ/9EZST/RGIh/0RnJv9HeTz/R3w//0d9P/9HfkH/R31A/0d9P/9HeTz/RW8v/0RpKf9FbS3/RGMi/0JZFv9CWhf/QloX/0JaF/9DWhf/QlkW/0NfHf9FbS3/Rng6/0VtLf9DXx3/QlkW/0JZFv9CWRf/Q1oX/0NZFv9CWBX/RGQi/0RlJP9DYiD/RWsq/0d7Pv9HfUD/R30//0d9QP9HfT//R3w//0Z4Ov9EYyL/Q10b/0VtLf9EaCf/Q14c/0NbGP9CWRb/QloX/0JZF/9CWRb/Q2Ih/0VqKv9FbCz/RWoq/0RkIv9DXx3/Q1sY/0JZFv9DWhf/QlkW/0JZFv9EaCj/RGUk/0NbGP9EZyb/R3s9/0d9QP9HfD//R31A/0d9QP9Hez7/RW0t/0NdGv9DWhf/RXAw/0VuL/9DYR//Q2Ae/0NcGv9DWhf/QlkW/0NcGf9EZyf/RW8w/0ZxMv9FbzD/RGcm/0NgHv9DYB7/Q1wZ/0JaF/9CWRb/Q14c/0VwMf9EYiD/QlkV/0NeG/9Gdjj/R3w//0d9P/9HfUD/R35A/0d8Pv9EZyb/Q10b/0NaF/9Fain/RnU3/0RpKP9DYSD/Q2Ae/0NdG/9DXBn/Q2Ef/0RmJf9Fbi7/RXAx/0VvMP9EZyb/Q2Eg/0NgHv9DXx3/Q1sZ/0NdGv9EaSn/RXEx/0NcGf9CWBX/Q1wa/0VsLP9HfD7/R30//0d9QP9HfkH/R3w//0VrK/9DYB7/Q1wZ/0RiIP9FcDH/RWsq/0NfHf9DYB7/Q18d/0NfHP9DYB7/RWoq/0ZxMv9GczT/RnQ1/0VsLP9DYR//Q2Ae/0NiIP9DYR//RGQj/0VtLv9Fbi7/Q1oY/0JZFv9CWRf/RGko/0d9P/9HfD//R31A/0d9QP9Gdjf/RWsr/0NhH/9DYB7/Q1wa/0NiIP9GcTL/RW4u/0VsLP9FbS3/RXEy/0Z0Nf9Gdjj/Rnc5/0Z3OP9Gdzn/Rnc4/0Z0Nf9GcTL/RXAx/0VuL/9FcTL/RnY3/0VrK/9DWhf/Q1oW/0NbGP9FcTL/R31A/0d9P/9HfUD/R31A/0Z2OP9EYyH/Q2Ae/0NhH/9DXhz/Q1wZ/0RnJv9Fbi7/RnY4/0Z3Of9HeDn/Rnc5/0Z3Of9Gdzn/Rnc4/0Z3Of9Gdzn/Rnc5/0Z4Ov9Gdzn/Rnc5/0Z3Of9Gdjf/RGQi/0NaF/9DXRr/Q2Ef/0ZzNP9HfD//R30//0d+Qf9HfUD/R3s+/0RnJv9DXhz/Q2Af/0NgHv9DXRv/Q18d/0NgHv9Fair/RnEy/0Z2OP9GdDX/RnY4/0Z3Of9Gdjj/Rnc5/0Z3Of9Gdjj/Rnc5/0Z3Of9GdTf/RnEy/0VuL/9DXx3/Q10b/0NgHv9DXx3/RW8v/0d9QP9HfT//R35A/0d9P/9HfUD/RnMz/0NhIP9DYR//Q2Ae/0NgH/9DXx3/Q1sY/0NgHv9DYiH/RW4u/0VrKv9Fayv/RnY3/0VxMf9FbzD/RnY3/0Z3Of9Gdzn/RnU3/0VvMP9EZCP/Q2Ae/0NfHP9DYB7/Q2Ae/0RkIv9HeDr/R31A/0d9P/9HfUD/Rnk6/0d9QP9HeTv/RGgn/0NhH/9DYR//Q2Ef/0NhH/9DXx3/Q2Ae/0NdGv9DXx3/RGUj/0NfHf9EZiX/RW4u/0RiIP9EaSn/RnU2/0Z3Of9GczX/RGcn/0NeHP9DXhz/Q2Af/0NhH/9DYR//RW8w/0d9P/9HfT//R31A/0d7Pf9Fbi7/R3w//0Z3Of9EaSn/Q2Ef/0NgH/9DYR//Q2Ef/0NhH/9DYR//Q2Ae/0NgHv9DXhz/Q18d/0NfHf9DYR//Q2Ef/0NfHf9EaCf/RnU2/0VuLv9DYiD/Q18d/0NhH/9DYR//Q2Ef/0RoJ/9Hejz/R31A/0d9QP9HfkH/RnIz/0RnJv9GdDb/R3w//0VuLv9DYB7/Q2Ae/0NhH/9EYiD/RGMh/0RiIP9DYR//Q2Ef/0NhH/9DYB7/Q2Ef/0NgHv9DXhz/Q2Ef/0NgH/9EZST/RGIg/0NhH/9DYSD/Q2Ig/0NhH/9DYiD/RWsr/0d5PP9HfUD/R31A/0Z3Of9EaCf/RGUk/0RpKP9GeDr/R3w+/0VtLP9DYR//Q2Af/0NhH/9EYiD/RGMh/0RiIP9DYR//Q2Eg/0NhH/9DYR//Q2Ef/0NhH/9DYR//Q2Af/0NfHf9DYR//RGIg/0NhH/9DYSD/Q2Ae/0RjIv9GcjP/R3w//0d9QP9Hej3/RWoq/0RmJf9EZiT/RGYl/0VrK/9Hejz/R3w+/0VvL/9EYiD/Q2Ef/0NgH/9DYR//Q2Eg/0NhH/9DYR//Q2Ef/0NhH/9DYR//Q2Ef/0NhH/9DYR//Q2Af/0NhH/9DYR//Q2Ef/0NhH/9EZST/RnM0/0d8P/9HfUD/R3s9/0VtLf9EZST/RGYl/0RmJf9EZiX/RGYl/0VsLP9Hejz/R35B/0Z0Nf9EZiT/Q2Ae/0NhH/9DYB//Q2Af/0NhH/9DYB//Q2Af/0RhH/9DYB//Q2Ef/0NhH/9DYR//Q2Ef/0NhH/9EYyL/RW0t/0Z5O/9HfUD/R31A/0d6PP9FbS3/RGYl/0RmJf9EZiX/RGYl/0RmJf9EZiX/RGYk/0VrKv9GeDr/R3w+/0VvMP9EZCP/Q2Ef/0NhH/9DYB7/Q2Ef/0NhH/9DYR//Q2Ef/0NgHv9DYB//Q2Af/0RjIf9Fain/RWsq/0VwMP9HfD7/R35A/0d9QP9Gdzn/RWoq/0RmJf9EZiX/RGYl/0RmJf9EZSX/RGYl/0RmJf9EZiX/RGYl/0RnJ/9GcjP/R3s9/0d6PP9GczT/RWsr/0RlJP9EYyH/Q2Ig/0NiIP9EYyH/RGcm/0RmJP9Fair/RnQ1/0d7Pf9HfD//R30//0d+Qf9HfD7/RXIy/0RoJ/9EZSX/RGYl/0RmJf9EZST/RGYl/0RmJf9EZiX/RGYl/0RmJf9EZiX/RGYl/0RmJf9FbCz/RnY4/0d8P/9HfD//R3k7/0Z1N/9GdDX/RnM0/0Z2N/9Hejz/Rnc4/0d6Pf9HfD7/R3s+/0d7Pv9Hej3/RnY4/0VsLP9EZiX/RGYl/0RmJf9EZiX/RGYl/0RlJP9EZyb/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=""" # For title bar and taskbar
logo_base64 = """/9j/4AAQSkZJRgABAQEAAAAAAAD/4QKyRXhpZgAATU0AKgAAAAgAAodpAAQAAAABAAABMuocAAcAAAEMAAAAJgAAAAAc6gAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAWQAwACAAAAFAAAAoCQBAACAAAAFAAAApSSkQACAAAAAzU2AACSkgACAAAAAzU2AADqHAAHAAABDAAAAXQAAAAAHOoAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADIwMjU6MDU6MTUgMTY6MDA6MzYAMjAyNTowNToxNSAxNjowMDozNgAAAP/hArBodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvADw/eHBhY2tldCBiZWdpbj0n77u/JyBpZD0nVzVNME1wQ2VoaUh6cmVTek5UY3prYzlkJz8+DQo8eDp4bXBtZXRhIHhtbG5zOng9ImFkb2JlOm5zOm1ldGEvIj48cmRmOlJERiB4bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiPjxyZGY6RGVzY3JpcHRpb24gcmRmOmFib3V0PSJ1dWlkOmZhZjViZGQ1LWJhM2QtMTFkYS1hZDMxLWQzM2Q3NTE4MmYxYiIgeG1sbnM6ZXhpZj0iaHR0cDovL25zLmFkb2JlLmNvbS9leGlmLzEuMC8iPjxleGlmOkRhdGVUaW1lT3JpZ2luYWw+MjAyNS0wNS0xNVQxNjowMDozNi41NjA8L2V4aWY6RGF0ZVRpbWVPcmlnaW5hbD48L3JkZjpEZXNjcmlwdGlvbj48L3JkZjpSREY+PC94OnhtcG1ldGE+DQogICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgCiAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgPD94cGFja2V0IGVuZD0ndyc/Pv/bAEMAAwICAwICAwMDAwQDAwQFCAUFBAQFCgcHBggMCgwMCwoLCw0OEhANDhEOCwsQFhARExQVFRUMDxcYFhQYEhQVFP/bAEMBAwQEBQQFCQUFCRQNCw0UFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFBQUFP/AABEIATUBBgMBIgACEQEDEQH/xAAfAAABBQEBAQEBAQAAAAAAAAAAAQIDBAUGBwgJCgv/xAC1EAACAQMDAgQDBQUEBAAAAX0BAgMABBEFEiExQQYTUWEHInEUMoGRoQgjQrHBFVLR8CQzYnKCCQoWFxgZGiUmJygpKjQ1Njc4OTpDREVGR0hJSlNUVVZXWFlaY2RlZmdoaWpzdHV2d3h5eoOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4eLj5OXm5+jp6vHy8/T19vf4+fr/xAAfAQADAQEBAQEBAQEBAAAAAAAAAQID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"""
 # For the loading overlay


# ------------------- UI Class -------------------
class AppUI:
    """
    Desktop UI with a two-column layout.
    
    LEFT PANEL:
      - Contains input fields for Name, Link, and Platform.
      - Primary buttons: "Add Account" and "Delete".
      - Secondary buttons: "Update Data", "Import CSV", and "Export CSV".
    
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

        ttk.Button(lf, text="Update Data", command=self.on_update_all).grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)
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
        """Handles the 'Add Account' button click."""
        name = self.name_var.get().strip()
        link = self.link_var.get().strip()
        plat = self.platform_var.get().strip()

        # --- DEBUG PRINT ---
        print(f"UI: Attempting to add: Name='{name}', Link='{link}', Platform='{plat}'")
        # --- END DEBUG PRINT ---

        if not (name and link and plat):
            messagebox.showerror("Input Error", "Please fill all fields.")
            return
        self.show_overlay("Adding...")
        
        def task():
            try:
                self.ctrl.add_account(name, link, plat)
            except Exception as ex: # Changed 'e' to 'ex' to avoid name collision in lambda
                # Capture the exception message at the time the lambda is created
                error_msg = str(ex)
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Add Error", msg))
            finally:
                self.root.after(0, self.hide_overlay)
                self.root.after(0, self.refresh)
                self.root.after(0, self.clear_inputs) # Clear inputs after adding

        threading.Thread(target=task, daemon=True).start()

    def on_update_all(self):
        """Handles the 'Update Data' button click."""
        self.show_overlay("Updating...")
        def task():
            try:
                self.ctrl.update_all()
            except Exception as ex: # Changed 'e' to 'ex'
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
            # Apply 'failed' tag for red background
            if len(row) > 4 and str(row[4]).lower() == "failed": # Check if category column exists
                tags = ("failed",)
            self.tree.insert("", "end", values=row, tags=tags)
        # The tag configuration is done once in __init__ now, but can be here too for dynamic changes.
        # self.tree.tag_configure("failed", background="#FFCCCC")


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
        print(f"Dummy: Added account {name} ({platform})")

    def delete_account(self, link):
        # Simulate deleting an account
        original_len = len(self.data)
        self.data = [r for r in self.data if r[1] != link]
        print(f"Dummy: Deleted account with link {link}. {original_len - len(self.data)} items removed.")

    def update_all(self):
        # Simulate updating all accounts
        print("Dummy: Updating all accounts...")
        new_data = []
        for rec in self.data:
            # Re-scrape each account
            new_rec = self.scrape_account((rec[0], rec[1], rec[2]))
            new_data.append(new_rec)
        self.data = new_data
        print("Dummy: All accounts updated.")

    def import_csv(self, path):
        """
        Dummy CSV import: reads name, link, and optionally platform.
        Mimics the main.py Controller's logic for platform determination.
        """
        print(f"Dummy: Importing CSV from {path}")
        try:
            with open(path, newline='', encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader) # Skip the header row (assuming your CSV has one)
                
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
        # Simulate success or failure based on link content
        if "fail" in link.lower():
            return (name, link, platform, 0, "failed")
        else:
            # Return some dummy follower count and category
            # Make follower count depend on name length for variety
            return (name, link, platform, 12345 + len(name) * 100, "micro")

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
