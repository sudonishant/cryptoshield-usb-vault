import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import time
import math
import os

class SecurityGUI:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        
        # Configure window properties
        self.root.title("CRYPTOSHIELD USB SECURE VAULT")
        self.root.geometry("1000x750")
        self.root.configure(bg="#08080f")
        self.root.resizable(False, False)
        
        # Colors
        self.bg_dark = "#08080f"
        self.bg_panel = "#10101f"
        self.accent_cyan = "#00f0ff"
        self.accent_green = "#00ff88"
        self.accent_red = "#ff2a5f"
        self.accent_amber = "#ffb700"
        self.text_white = "#ffffff"
        self.text_dim = "#7d7f9c"
        
        # State variables
        self.entered_pin = ""
        self.cap = None
        self.is_camera_running = False
        self.webcam_canvas_image = None
        self.is_unlocked = False
        
        self.drives_list = [] # List of drive dicts from controller
        
        # Setup styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background=self.bg_dark, foreground=self.text_white)
        self.style.configure("TNotebook", background=self.bg_dark, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=self.bg_panel, foreground=self.text_dim, 
                             padding=[20, 10], font=("Helvetica", 10, "bold"))
        self.style.map("TNotebook.Tab", 
                       background=[("selected", self.accent_cyan)], 
                       foreground=[("selected", "#08080f")])
        self.style.configure("TCombobox", 
                              fieldbackground="#05050a", 
                              background="#17172e", 
                              foreground=self.text_white)
        
        self.create_widgets()
        
    def create_widgets(self):
        # 1. Title Banner
        self.title_frame = tk.Frame(self.root, bg=self.bg_dark, height=65)
        self.title_frame.pack(fill="x", padx=20, pady=(10, 5))
        
        self.title_lbl = tk.Label(
            self.title_frame, 
            text="CRYPTOSHIELD // BIOMETRIC VAULT UNLOCKER", 
            font=("Courier New", 20, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_dark
        )
        self.title_lbl.pack(side="left")
        
        self.status_indicator = tk.Label(
            self.title_frame, 
            text="● SCANNING DRIVE", 
            font=("Courier New", 12, "bold"), 
            fg=self.accent_amber, 
            bg=self.bg_dark,
            padx=15
        )
        self.status_indicator.pack(side="right", pady=5)
        
        # 2. Notebook container for auth tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Tab 1: Access Control
        self.tab_access = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_access, text=" ACCESS CONTROLLER ")
        
        # Tab 2: Setup Wizard
        self.tab_setup = tk.Frame(self.notebook, bg=self.bg_dark)
        self.notebook.add(self.tab_setup, text=" SECURE ENROLLMENT ")
        
        # Populate Tabs
        self.build_access_tab()
        self.build_setup_tab()
        
        # 3. Secure File Explorer Dashboard (hidden initially)
        self.build_explorer_frame()
        
        # 4. Bottom Status Console
        self.console_frame = tk.LabelFrame(
            self.root, 
            text=" SECURITY TERMINAL LOGS ", 
            font=("Courier New", 9, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        self.console_frame.pack(fill="x", padx=20, pady=(5, 15), side="bottom")
        
        self.console_text = tk.Text(
            self.console_frame, 
            height=6, 
            bg="#05050a", 
            fg=self.accent_green, 
            font=("Courier New", 10), 
            bd=0, 
            padx=10, 
            pady=5
        )
        self.console_text.pack(fill="both", expand=True)
        self.console_text.config(state="disabled")
        
        self.log("CryptoShield Container-Based Vault Core Initialized. Awaiting USB...")

    def build_access_tab(self):
        # Left Panel: Camera Stream (webcam)
        self.cam_panel = tk.LabelFrame(
            self.tab_access, 
            text=" BIOMETRIC SCANNER (FACE ID) ", 
            font=("Courier New", 10, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        self.cam_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.cam_canvas = tk.Canvas(self.cam_panel, bg="#05050a", bd=0, highlightthickness=0)
        self.cam_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Right Panel: PIN Entry and Control
        self.control_panel = tk.Frame(self.tab_access, bg=self.bg_dark, width=350)
        self.control_panel.pack(side="right", fill="both", padx=10, pady=10)
        self.control_panel.pack_propagate(False)
        
        # USB Drive Selector Frame
        self.usb_select_frame = tk.LabelFrame(
            self.control_panel, 
            text=" 1. TARGET USB DRIVE ", 
            font=("Courier New", 10, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        self.usb_select_frame.pack(fill="x", pady=(0, 10))
        
        self.drive_var = tk.StringVar()
        
        self.drive_select_inner = tk.Frame(self.usb_select_frame, bg=self.bg_panel)
        self.drive_select_inner.pack(fill="x", padx=10, pady=8)
        
        self.drive_combo = ttk.Combobox(
            self.drive_select_inner, 
            textvariable=self.drive_var, 
            state="readonly",
            font=("Helvetica", 9),
            width=25
        )
        self.drive_combo.pack(side="left", fill="x", expand=True)
        self.drive_combo.bind("<<ComboboxSelected>>", self.on_drive_selected)
        
        self.btn_browse = tk.Button(
            self.drive_select_inner,
            text="Browse...",
            font=("Helvetica", 9),
            bg="#17172e",
            fg=self.accent_cyan,
            activebackground=self.accent_cyan,
            activeforeground="#08080f",
            bd=0,
            padx=8,
            command=self.browse_directory
        )
        self.btn_browse.pack(side="right", padx=(5, 0))
        
        # PIN Entry Pad
        self.pin_pad_frame = tk.LabelFrame(
            self.control_panel, 
            text=" 2. SECURE PIN LOCK ", 
            font=("Courier New", 10, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        self.pin_pad_frame.pack(fill="both", expand=True)
        
        # Display Box for PIN
        self.pin_display_var = tk.StringVar(value="ENTER PIN")
        self.pin_display = tk.Label(
            self.pin_pad_frame, 
            textvariable=self.pin_display_var, 
            font=("Courier New", 18, "bold"), 
            bg="#05050a", 
            fg=self.accent_amber, 
            height=2, 
            relief="solid", 
            bd=1
        )
        self.pin_display.pack(fill="x", padx=15, pady=10)
        
        # Numeric keypad
        self.numpad_grid = tk.Frame(self.pin_pad_frame, bg=self.bg_panel)
        self.numpad_grid.pack(expand=True, padx=10, pady=5)
        
        buttons = [
            '1', '2', '3',
            '4', '5', '6',
            '7', '8', '9',
            'CLEAR', '0', 'UNLOCK'
        ]
        
        for i, label in enumerate(buttons):
            row = i // 3
            col = i % 3
            
            btn_bg = "#17172e"
            btn_fg = self.text_white
            if label == "CLEAR":
                btn_bg = "#2b172a"
                btn_fg = self.accent_red
            elif label == "UNLOCK":
                btn_bg = "#14332e"
                btn_fg = self.accent_green
                
            btn = tk.Button(
                self.numpad_grid, 
                text=label, 
                font=("Helvetica", 11, "bold"), 
                bg=btn_bg, 
                fg=btn_fg, 
                activebackground=self.accent_cyan, 
                activeforeground="#08080f", 
                bd=0, 
                width=8, 
                height=2,
                command=lambda x=label: self.press_key(x)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

    def build_setup_tab(self):
        self.setup_container = tk.LabelFrame(
            self.tab_setup, 
            text=" CONFIGURE CONTAINER PROTECTION ", 
            font=("Courier New", 12, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        self.setup_container.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Info/Warning label
        self.warning_lbl = tk.Label(
            self.setup_container,
            text="💡 INFO: Files will be moved into an encrypted container (.secure_vault/) on the USB.\nThis does not format the drive and is completely safe. The USB remains readable on any OS.",
            font=("Helvetica", 9, "bold"),
            fg=self.accent_cyan,
            bg=self.bg_panel,
            justify=tk.LEFT
        )
        self.warning_lbl.pack(anchor="w", padx=20, pady=(15, 5))

        # Step 1: Select Drive Dropdown
        tk.Label(
            self.setup_container, 
            text="Step 1: Select target USB drive path", 
            font=("Helvetica", 11, "bold"), 
            fg=self.text_white, 
            bg=self.bg_panel
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.setup_drive_select_inner = tk.Frame(self.setup_container, bg=self.bg_panel)
        self.setup_drive_select_inner.pack(anchor="w", fill="x", padx=20, pady=5)
        
        self.setup_drive_var = tk.StringVar()
        self.setup_drive_combo = ttk.Combobox(
            self.setup_drive_select_inner, 
            textvariable=self.setup_drive_var, 
            state="readonly",
            font=("Helvetica", 10),
            width=50
        )
        self.setup_drive_combo.pack(side="left")
        self.setup_drive_combo.bind("<<ComboboxSelected>>", self.on_setup_drive_selected)
        
        self.btn_setup_browse = tk.Button(
            self.setup_drive_select_inner,
            text="Browse...",
            font=("Helvetica", 9),
            bg="#17172e",
            fg=self.accent_cyan,
            activebackground=self.accent_cyan,
            activeforeground="#08080f",
            bd=0,
            padx=12,
            pady=2,
            command=self.browse_setup_directory
        )
        self.btn_setup_browse.pack(side="left", padx=(10, 0))
        
        # Step 2: Set PIN
        tk.Label(
            self.setup_container, 
            text="Step 2: Enter new secure numeric PIN (4-8 digits)", 
            font=("Helvetica", 11, "bold"), 
            fg=self.text_white, 
            bg=self.bg_panel
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.setup_pin_entry = tk.Entry(
            self.setup_container, 
            show="*", 
            bg="#05050a", 
            fg=self.accent_amber, 
            bd=0, 
            insertbackground=self.accent_cyan, 
            font=("Helvetica", 14, "bold"), 
            width=15
        )
        self.setup_pin_entry.pack(anchor="w", padx=20, pady=5)
        
        # Step 2.5: Set Custom Drive Label/Name
        tk.Label(
            self.setup_container, 
            text="Step 2.5: Enter custom vault name (Optional)", 
            font=("Helvetica", 11, "bold"), 
            fg=self.text_white, 
            bg=self.bg_panel
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.setup_label_entry = tk.Entry(
            self.setup_container, 
            bg="#05050a", 
            fg=self.accent_cyan, 
            bd=0, 
            insertbackground=self.accent_cyan, 
            font=("Helvetica", 12, "bold"), 
            width=20
        )
        self.setup_label_entry.pack(anchor="w", padx=20, pady=5)
        self.setup_label_entry.insert(0, "SecureUSB")
        
        # Step 3: Biometric Enrollment
        tk.Label(
            self.setup_container, 
            text="Step 3: Biometric Enrollment (Webcam Face scan)", 
            font=("Helvetica", 11, "bold"), 
            fg=self.text_white, 
            bg=self.bg_panel
        ).pack(anchor="w", padx=20, pady=(15, 5))
        
        self.enroll_btn_frame = tk.Frame(self.setup_container, bg=self.bg_panel)
        self.enroll_btn_frame.pack(fill="x", padx=20, pady=5)
        
        self.btn_enroll_face = tk.Button(
            self.enroll_btn_frame, 
            text="START BIOMETRIC SCANNING", 
            command=self.start_face_enrollment, 
            bg="#143014", 
            fg=self.accent_green, 
            activebackground=self.accent_green, 
            activeforeground="#08080f", 
            bd=0, 
            padx=15, 
            pady=8,
            font=("Helvetica", 10, "bold")
        )
        self.btn_enroll_face.pack(side="left")
        
        self.enroll_status_lbl = tk.Label(
            self.enroll_btn_frame, 
            text="Ready to capture facial profile...", 
            font=("Helvetica", 10, "italic"), 
            fg=self.text_dim, 
            bg=self.bg_panel,
            padx=15
        )
        self.enroll_status_lbl.pack(side="left", fill="y")
        
        # Step 4: Finalize button
        self.btn_setup_vault = tk.Button(
            self.setup_container, 
            text="INITIALIZE SECURE VAULT & LOCK DRIVE", 
            command=self.finalize_vault_setup, 
            bg=self.accent_cyan, 
            fg="#08080f", 
            activebackground=self.accent_green, 
            activeforeground="#08080f", 
            bd=0, 
            pady=12,
            font=("Helvetica", 11, "bold")
        )
        self.btn_setup_vault.pack(fill="x", padx=20, pady=20, side="bottom")

    def build_explorer_frame(self):
        """Creates the Secure Explorer UI Panel displayed after successful vault unlock."""
        self.explorer_frame = tk.Frame(self.root, bg=self.bg_dark)
        
        # 1. Toolbar Frame
        self.toolbar = tk.Frame(self.explorer_frame, bg=self.bg_panel, height=50)
        self.toolbar.pack(fill="x", side="top", padx=10, pady=(5, 5))
        self.toolbar.pack_propagate(False)
        
        # Configure button styles
        btn_style = {"font": ("Helvetica", 9, "bold"), "bd": 0, "padx": 10, "pady": 5}
        
        self.btn_add_file = tk.Button(
            self.toolbar, text="➕ ADD FILE", bg="#14332e", fg=self.accent_green,
            activebackground=self.accent_green, activeforeground="#08080f",
            command=self.controller.add_file_click, **btn_style
        )
        self.btn_add_file.pack(side="left", padx=5, pady=5)

        self.btn_add_folder = tk.Button(
            self.toolbar, text="📁 ADD FOLDER", bg="#14332e", fg=self.accent_green,
            activebackground=self.accent_green, activeforeground="#08080f",
            command=self.controller.add_folder_click, **btn_style
        )
        self.btn_add_folder.pack(side="left", padx=5, pady=5)
        
        self.btn_extract = tk.Button(
            self.toolbar, text="💾 EXTRACT SELECTED", bg="#172e3d", fg=self.accent_cyan,
            activebackground=self.accent_cyan, activeforeground="#08080f",
            command=self.controller.extract_selected_click, **btn_style
        )
        self.btn_extract.pack(side="left", padx=5, pady=5)
        
        self.btn_delete = tk.Button(
            self.toolbar, text="🗑️ SHRED & DELETE", bg="#36171d", fg=self.accent_red,
            activebackground=self.accent_red, activeforeground="#08080f",
            command=self.controller.delete_selected_click, **btn_style
        )
        self.btn_delete.pack(side="left", padx=5, pady=5)
        
        self.btn_lock_vault = tk.Button(
            self.toolbar, text="🔒 LOCK & CLOSE", bg="#2b1a10", fg=self.accent_amber,
            activebackground=self.accent_amber, activeforeground="#08080f",
            command=self.controller.lock_drive_click, **btn_style
        )
        self.btn_lock_vault.pack(side="right", padx=5, pady=5)
        
        self.btn_unprotect = tk.Button(
            self.toolbar, text="🔓 UNPROTECT USB", bg="#2b1a10", fg=self.accent_amber,
            activebackground=self.accent_amber, activeforeground="#08080f",
            command=self.controller.unprotect_drive_click, **btn_style
        )
        self.btn_unprotect.pack(side="right", padx=5, pady=5)
        
        # 2. Path Breadcrumb
        self.path_lbl = tk.Label(
            self.explorer_frame, text="Vault Path: Root", font=("Courier New", 10, "bold"),
            fg=self.accent_cyan, bg=self.bg_dark, anchor="w", padx=15
        )
        self.path_lbl.pack(fill="x", side="top", pady=(2, 2))
        
        # 3. Main Treeview panel
        self.tree_frame = tk.Frame(self.explorer_frame, bg=self.bg_dark)
        self.tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Scrollbars
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical")
        self.hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal")
        
        # Treeview Configuration
        self.style.configure("Treeview", 
                             background="#10101f", 
                             foreground="#ffffff", 
                             fieldbackground="#10101f",
                             rowheight=26,
                             font=("Helvetica", 10))
        self.style.map("Treeview", 
                       background=[("selected", "#00f0ff")], 
                       foreground=[("selected", "#08080f")])
        self.style.configure("Treeview.Heading", 
                             background="#17172e", 
                             foreground=self.accent_cyan, 
                             font=("Courier New", 10, "bold"))
        
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=("Size", "Type", "Path"),
            yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set,
            selectmode="extended"
        )
        
        self.vsb.config(command=self.tree.yview)
        self.hsb.config(command=self.tree.xview)
        
        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        
        # Set headings
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("Size", text="Size", anchor="w")
        self.tree.heading("Type", text="Type", anchor="w")
        self.tree.heading("Path", text="Vault Relative Path", anchor="w")
        
        # Set column widths
        self.tree.column("#0", width=300, minwidth=150)
        self.tree.column("Size", width=100, minwidth=50)
        self.tree.column("Type", width=100, minwidth=50)
        self.tree.column("Path", width=350, minwidth=150)
        
        # Bindings
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        
        # 4. Status Bar
        self.stats_bar = tk.Frame(self.explorer_frame, bg=self.bg_panel, height=25)
        self.stats_bar.pack(fill="x", side="bottom", padx=10, pady=(5, 5))
        self.stats_bar.pack_propagate(False)
        
        self.stats_lbl = tk.Label(
            self.stats_bar, text="0 Items | Total Size: 0 Bytes",
            font=("Helvetica", 9), fg=self.text_dim, bg=self.bg_panel, anchor="w", padx=10
        )
        self.stats_lbl.pack(fill="both", expand=True)

    def browse_directory(self):
        dir_path = filedialog.askdirectory(title="Select USB Mount Directory")
        if dir_path:
            self.controller.select_device_by_path(dir_path)
            self.log(f"Manually browsed and selected USB directory: {dir_path}")

    def browse_setup_directory(self):
        dir_path = filedialog.askdirectory(title="Select USB Setup Directory")
        if dir_path:
            self.controller.select_device_by_path(dir_path)
            self.setup_drive_var.set(dir_path)
            self.drive_var.set(dir_path)
            self.log(f"Manually browsed setup USB directory: {dir_path}")

    def update_drives_dropdown(self, drives):
        """Populates the dropdown elements with active drive values."""
        self.drives_list = drives
        options = []
        for d in drives:
            options.append(f"{d['path']} ({d['size']}) - {d['model']}")
            
        self.drive_combo['values'] = options
        self.setup_drive_combo['values'] = options
        
        if options:
            # Check if current selection is still valid
            current_sel = self.drive_var.get()
            if not current_sel or current_sel not in options:
                self.drive_combo.current(0)
                self.setup_drive_combo.current(0)
                self.drive_var.set(options[0])
                self.setup_drive_var.set(options[0])
                self.controller.select_device_by_path(drives[0]["path"])
        else:
            self.drive_combo['values'] = []
            self.setup_drive_combo['values'] = []
            self.drive_var.set("")
            self.setup_drive_var.set("")

    def on_drive_selected(self, event):
        idx = self.drive_combo.current()
        if idx >= 0 and idx < len(self.drives_list):
            path = self.drives_list[idx]["path"]
            self.controller.select_device_by_path(path)
            self.setup_drive_combo.current(idx)
            self.setup_drive_var.set(self.setup_drive_combo.get())
            self.log(f"Target drive selected: {path}")

    def on_setup_drive_selected(self, event):
        idx = self.setup_drive_combo.current()
        if idx >= 0 and idx < len(self.drives_list):
            path = self.drives_list[idx]["path"]
            self.controller.select_device_by_path(path)
            self.drive_combo.current(idx)
            self.drive_var.set(self.drive_combo.get())
            self.log(f"Setup drive selected: {path}")

    def format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def populate_explorer(self, files_dict):
        """Populates the Secure Explorer Treeview with the flat vault file dictionary."""
        # Clear the treeview first
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        node_map = {}
        total_size = 0
        total_files = 0
        
        # Sort files so directories are processed first
        for rel_path in sorted(files_dict.keys()):
            parts = rel_path.split('/')
            
            for i, part in enumerate(parts):
                current_path = "/".join(parts[:i+1])
                is_file = (i == len(parts) - 1)
                
                if current_path not in node_map:
                    parent_node = node_map.get("/".join(parts[:i]), "")
                    if is_file:
                        file_info = files_dict[rel_path]
                        size_bytes = file_info.get("size", 0)
                        total_size += size_bytes
                        total_files += 1
                        size_str = self.format_size(size_bytes)
                        node_id = self.tree.insert(parent_node, "end", text=part, values=(size_str, "File", rel_path))
                    else:
                        node_id = self.tree.insert(parent_node, "end", text=part, values=("", "Folder", current_path))
                    node_map[current_path] = node_id
                    
        # Update Stats Bar
        self.stats_lbl.config(
            text=f"{total_files} Files | Total Encrypted Size: {self.format_size(total_size)}"
        )

    def on_tree_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        values = self.tree.item(item, "values")
        if not values:
            return
        size, file_type, rel_path = values
        if file_type == "File":
            self.log(f"Requesting temp decrypt and open: {rel_path}...")
            self.controller.handle_open_file(rel_path)

    def on_tree_select(self, event):
        selected = self.tree.selection()
        if not selected:
            self.path_lbl.config(text="Vault Path: Root")
            return
        
        # Show relative path of the first selected item
        values = self.tree.item(selected[0], "values")
        if values:
            self.path_lbl.config(text=f"Vault Path: {values[2]}")

    def show_vault_explorer(self, files_dict):
        """Transitions UI layout to show Secure File Explorer panel."""
        self.is_unlocked = True
        self.stop_camera()
        
        # Hide standard Notebook tabs
        self.notebook.pack_forget()
        
        # Populate explorer
        self.populate_explorer(files_dict)
        
        # Display Explorer Panel
        self.explorer_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.set_status("● UNLOCKED", "success")
        self.pin_display_var.set("UNLOCKED")

    def hide_vault_explorer(self):
        """Hides the Secure Explorer and restores the authentication panel."""
        self.is_unlocked = False
        
        # Hide Explorer
        self.explorer_frame.pack_forget()
        
        # Restore Notebook tabs
        self.notebook.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Restart camera
        self.start_camera()
        
        self.set_status("● SECURED", "secure")
        self.entered_pin = ""
        self.pin_display_var.set("ENTER PIN")

    def show_unlock_tab(self):
        self.notebook.select(0)

    def show_setup_tab(self):
        self.notebook.select(1)

    def log(self, message: str):
        self.console_text.config(state="normal")
        timestamp = time.strftime("[%H:%M:%S] ")
        self.console_text.insert(tk.END, timestamp + message + "\n")
        self.console_text.see(tk.END)
        self.console_text.config(state="disabled")

    def set_status(self, text: str, mode: str = "secure"):
        self.status_indicator.config(text=text)
        if mode == "secure":
            self.status_indicator.config(fg=self.accent_red)
        elif mode == "warning":
            self.status_indicator.config(fg=self.accent_amber)
        elif mode == "success":
            self.status_indicator.config(fg=self.accent_green)

    def press_key(self, char):
        if self.is_unlocked:
            return
        if char == "CLEAR":
            self.entered_pin = ""
            self.pin_display_var.set("ENTER PIN")
        elif char == "UNLOCK":
            self.trigger_unlock()
        else:
            if self.pin_display_var.get() == "ENTER PIN" or self.pin_display_var.get() == "RETRY PIN":
                self.entered_pin = ""
            if len(self.entered_pin) < 8:
                self.entered_pin += char
                self.pin_display_var.set("● " * len(self.entered_pin))

    def trigger_unlock(self):
        if not self.drive_var.get():
            messagebox.showerror("Error", "No USB drive directory selected!")
            return
        if not self.entered_pin:
            messagebox.showerror("Error", "Please enter your security PIN!")
            return
        self.log("Verifying credentials and decrypting vault index...")
        self.controller.handle_unlock_request(self.entered_pin)

    def start_face_enrollment(self):
        if not self.setup_drive_var.get():
            messagebox.showerror("Error", "Please select a target USB directory first!")
            return
            
        pin = self.setup_pin_entry.get()
        if len(pin) < 4 or len(pin) > 8 or not pin.isdigit():
            messagebox.showerror("Error", "PIN must be between 4 and 8 digits!")
            return
            
        self.log("Opening camera for biometric profile enrollment. Look at the webcam.")
        self.btn_enroll_face.config(state="disabled")
        self.controller.handle_face_enrollment(pin)

    def finalize_vault_setup(self):
        pin = self.setup_pin_entry.get()
        label = self.setup_label_entry.get().strip() or "SecureUSB"
        self.controller.handle_finalize_vault(pin, label)

    def start_camera(self):
        if self.is_camera_running or self.is_unlocked:
            return
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.log("[ERROR] Webcam could not be loaded. Running standard PIN mode.")
            self.draw_no_camera()
            return
        self.is_camera_running = True
        self.log("Webcam live feed engaged. Biometric verification active.")
        self.update_camera_feed()

    def stop_camera(self):
        self.is_camera_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.cam_canvas.delete("all")
        self.log("Webcam feed shut down.")

    def draw_no_camera(self):
        self.cam_canvas.delete("all")
        self.cam_canvas.create_rectangle(10, 10, 600, 400, fill="#05050a", outline=self.accent_amber, width=1)
        self.cam_canvas.create_text(
            280, 150, 
            text="[ WEBCAM NOT FOUND OR ACCESSED ]\n\nPIN Entry Fallback mode is active.\nEnrollment requires webcam connection.", 
            fill=self.accent_amber, 
            font=("Courier New", 11, "bold"),
            justify=tk.CENTER
        )

    def update_camera_feed(self):
        if not self.is_camera_running or not self.cap or self.is_unlocked:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.root.after(15, self.update_camera_feed)
            return

        # Flip horizontally
        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape
        
        # Get face authentication details from controller
        gray_face, bbox, matching_info = self.controller.process_camera_frame(frame)
        
        # Draw HUD overlays
        border_color = (255, 240, 0) # BGR
        length = 25
        # Corner lines
        cv2.line(frame, (10, 10), (10 + length, 10), border_color, 1)
        cv2.line(frame, (10, 10), (10, 10 + length), border_color, 1)
        cv2.line(frame, (width - 10, 10), (width - 10 - length, 10), border_color, 1)
        cv2.line(frame, (width - 10, 10), (width - 10, 10 + length), border_color, 1)
        cv2.line(frame, (10, height - 10), (10 + length, height - 10), border_color, 1)
        cv2.line(frame, (10, height - 10), (10, height - 10 - length), border_color, 1)
        cv2.line(frame, (width - 10, height - 10), (width - 10 - length, height - 10), border_color, 1)
        cv2.line(frame, (width - 10, height - 10), (width - 10, height - 10 - length), border_color, 1)

        # Rotating Radar
        radar_center = (width - 55, 55)
        radar_radius = 30
        cv2.circle(frame, radar_center, radar_radius, (100, 100, 100), 1)
        cv2.circle(frame, radar_center, radar_radius - 10, (50, 50, 50), 1)
        angle = int((time.time() * 6) % 360)
        radar_x = int(radar_center[0] + radar_radius * math.cos(math.radians(angle)))
        radar_y = int(radar_center[1] + radar_radius * math.sin(math.radians(angle)))
        cv2.line(frame, radar_center, (radar_x, radar_y), (0, 255, 136), 1)
        if int(time.time() * 2) % 2 == 0:
            cv2.circle(frame, radar_center, 3, (0, 255, 136), -1)

        # Telemetry
        cv2.putText(frame, "CRYPTOSHIELD SECURE VAULT v3.0", (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 240, 0), 1)
        cv2.putText(frame, "ENGINE: AES-256-GCM VAULT ENCRYPTOR", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 240, 0), 1)
        
        status_text = "LOCK STATUS: UNINITIALIZED"
        status_color = (95, 183, 255) # BGR
        
        if self.controller.face_auth.is_trained:
            if self.controller.face_match_status:
                status_text = "SYS STATUS: FACE ACCESS CONFIRMED"
                status_color = (136, 255, 0)
            else:
                status_text = "SYS STATUS: AWAITING BIO MATCH"
                status_color = (0, 42, 255)
        cv2.putText(frame, status_text, (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)

        # Face targeting box
        if bbox is not None:
            x, y, w, h = bbox
            color = (136, 255, 0) if matching_info.get("match", False) else (0, 183, 255)
            
            t_len = 20
            t_thick = 2
            cv2.line(frame, (x, y), (x + t_len, y), color, t_thick)
            cv2.line(frame, (x, y), (x, y + t_len), color, t_thick)
            cv2.line(frame, (x + w, y), (x + w - t_len, y), color, t_thick)
            cv2.line(frame, (x + w, y), (x + w, y + t_len), color, t_thick)
            cv2.line(frame, (x, y + h), (x + t_len, y + h), color, t_thick)
            cv2.line(frame, (x, y + h), (x, y + h - t_len), color, t_thick)
            cv2.line(frame, (x + w, y + h), (x + w - t_len, y + h), color, t_thick)
            cv2.line(frame, (x + w, y + h), (x + w, y + h - t_len), color, t_thick)
            
            cx, cy = x + w//2, y + h//2
            cv2.line(frame, (cx - 10, cy), (cx + 10, cy), color, 1)
            cv2.line(frame, (cx, cy - 10), (cx, cy + 10), color, 1)
            
            cv2.putText(frame, "TARGET LOCK INITIATED", (x, y - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            cv2.putText(frame, f"BIO MATCH: {matching_info.get('confidence', '')}", (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)
            
            if matching_info.get("verifying", False):
                pulsing_val = int((math.sin(time.time() * 8) + 1) * 127)
                alert_color = (0, pulsing_val, pulsing_val + 100)
                cv2.putText(frame, "SCANNING BIOMETRICS...", (30, height - 30), 
                            cv2.FONT_HERSHEY_COMPLEX, 0.5, alert_color, 1)
        else:
            cv2.putText(frame, "AWAITING TARGET FACE", (30, height - 30), 
                        cv2.FONT_HERSHEY_COMPLEX, 0.5, (150, 150, 150), 1)

        # Convert to PIL and show
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        canvas_width = self.cam_canvas.winfo_width()
        canvas_height = self.cam_canvas.winfo_height()
        if canvas_width > 10 and canvas_height > 10:
            img_pil = img_pil.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BICUBIC)
            
        self.webcam_canvas_image = ImageTk.PhotoImage(img_pil)
        self.cam_canvas.create_image(0, 0, anchor="nw", image=self.webcam_canvas_image)
        
        scan_y = int((time.time() * 180) % canvas_height)
        self.cam_canvas.create_line(0, scan_y, canvas_width, scan_y, fill="#00f0ff", width=1, dash=(8, 4))
        
        self.root.after(15, self.update_camera_feed)
