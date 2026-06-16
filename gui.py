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
        self.root.configure(bg="#020205")
        self.root.resizable(False, False)
        
        # Sci-Fi / Cyberpunk Color Palette
        self.bg_dark = "#020205"
        self.bg_panel = "#080815"
        self.bg_well = "#04040a"
        self.accent_cyan = "#00f0ff"
        self.accent_green = "#00ff66"
        self.accent_red = "#ff0055"
        self.accent_amber = "#ffb700"
        self.text_white = "#ffffff"
        self.text_dim = "#5a5d7a"
        
        # State variables
        self.entered_pin = ""
        self.cap = None
        self.is_camera_running = False
        self.webcam_canvas_image = None
        self.is_unlocked = False
        
        self.drives_list = []
        self.current_state = "SCANNING"  # SCANNING, PROMPT_SECURE, SETUP_SECURE, ACCESS_GATE, SECURE_EXPLORER
        
        # Setup ttk styles for Sci-Fi look
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(".", background=self.bg_dark, foreground=self.text_white)
        self.style.configure("TCombobox", 
                             fieldbackground="#05050f", 
                             background="#101026", 
                             foreground=self.accent_cyan,
                             arrowcolor=self.accent_cyan)
        
        # Create persistent widget instances to maintain main.py references
        self.create_persistent_widgets()
        
        # Build main layout
        self.build_main_layout()
        
        # Initialize state
        self.set_state("SCANNING")

    def create_persistent_widgets(self):
        """Creates all widgets that main.py expects to refer to directly, ensuring compatibility."""
        # Drive Variables & Dropdowns
        self.drive_var = tk.StringVar()
        self.setup_drive_var = tk.StringVar()
        
        self.drive_combo = ttk.Combobox(self.root, textvariable=self.drive_var, state="readonly")
        self.setup_drive_combo = ttk.Combobox(self.root, textvariable=self.setup_drive_var, state="readonly")
        
        # PIN inputs & Status indicators
        self.setup_pin_entry = tk.Entry(self.root, show="*", bg="#05050f", fg=self.accent_amber, bd=1, insertbackground=self.accent_cyan)
        self.setup_label_entry = tk.Entry(self.root, bg="#05050f", fg=self.accent_cyan, bd=1, insertbackground=self.accent_cyan)
        self.setup_label_entry.insert(0, "SecureUSB")
        
        self.pin_display_var = tk.StringVar(value="ENTER PIN")
        
        # Biometric state elements
        self.enroll_status_lbl = tk.Label(self.root, text="Ready...", fg=self.text_dim, bg=self.bg_panel)
        
        # Buttons
        self.btn_enroll_face = tk.Button(self.root, text="SCAN", command=self.start_face_enrollment)
        self.btn_setup_vault = tk.Button(self.root, text="LOCK", command=self.finalize_vault_setup)
        
        # Canvas for camera stream
        self.cam_canvas = tk.Canvas(self.root, bg="#000000", bd=0, highlightthickness=1, highlightbackground=self.accent_cyan)
        
        # Treeview for File Explorer
        self.vsb = ttk.Scrollbar(self.root, orient="vertical")
        self.hsb = ttk.Scrollbar(self.root, orient="horizontal")
        
        self.style.configure("Treeview", 
                             background=self.bg_panel, 
                             foreground=self.text_white, 
                             fieldbackground=self.bg_panel,
                             rowheight=26,
                             font=("Helvetica", 10))
        self.style.map("Treeview", 
                       background=[("selected", self.accent_cyan)], 
                       foreground=[("selected", self.bg_dark)])
        self.style.configure("Treeview.Heading", 
                             background="#0d0d26", 
                             foreground=self.accent_cyan, 
                             font=("Courier New", 9, "bold"))
        
        self.tree = ttk.Treeview(
            self.root,
            columns=("Size", "Type", "Path"),
            yscrollcommand=self.vsb.set,
            xscrollcommand=self.hsb.set,
            selectmode="extended"
        )
        self.tree.heading("#0", text="Name", anchor="w")
        self.tree.heading("Size", text="Size", anchor="w")
        self.tree.heading("Type", text="Type", anchor="w")
        self.tree.heading("Path", text="Vault Relative Path", anchor="w")
        self.tree.column("#0", width=250, minwidth=150)
        self.tree.column("Size", width=80, minwidth=50)
        self.tree.column("Type", width=80, minwidth=50)
        self.tree.column("Path", width=300, minwidth=150)
        
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def build_main_layout(self):
        # 1. Top Cyberpunk HUD Banner
        self.hud_header = tk.Frame(self.root, bg=self.bg_dark, height=60)
        self.hud_header.pack(fill="x", padx=20, pady=(10, 5))
        self.hud_header.pack_propagate(False)
        
        # Grid line below header
        header_grid = tk.Frame(self.root, bg=self.accent_cyan, height=1)
        header_grid.pack(fill="x", padx=20, pady=(0, 5))
        
        self.title_lbl = tk.Label(
            self.hud_header, 
            text="CRYPTOSHIELD // SECURITY VAULT CORE", 
            font=("Courier New", 18, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_dark
        )
        self.title_lbl.pack(side="left", pady=10)
        
        self.status_indicator = tk.Label(
            self.hud_header, 
            text="● SCANNING INTERFACE", 
            font=("Courier New", 11, "bold"), 
            fg=self.accent_amber, 
            bg=self.bg_dark,
            padx=15
        )
        self.status_indicator.pack(side="right", pady=15)
        
        # 2. Main Dynamic View Container
        self.view_container = tk.Frame(self.root, bg=self.bg_dark)
        self.view_container.pack(fill="both", expand=True, padx=20, pady=5)
        
        # 3. Bottom Terminal Log Console
        console_grid = tk.Frame(self.root, bg=self.accent_cyan, height=1)
        console_grid.pack(fill="x", padx=20, pady=(5, 0))
        
        self.console_frame = tk.LabelFrame(
            self.root, 
            text=" SYSTEM CORE DIAGNOSTICS LOGS ", 
            font=("Courier New", 8, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        self.console_frame.pack(fill="x", padx=20, pady=(5, 15), side="bottom")
        
        self.console_text = tk.Text(
            self.console_frame, 
            height=5, 
            bg=self.bg_well, 
            fg=self.accent_green, 
            font=("Courier New", 9), 
            bd=0, 
            padx=10, 
            pady=5
        )
        self.console_text.pack(fill="both", expand=True)
        self.console_text.config(state="disabled")
        
        self.log("CryptoShield Cryptographic Controller Initialized. Listening for storage events...")

    def set_state(self, state_name):
        """Transition interface to a new state and render corresponding widgets."""
        self.log(f"[STATE SYSTEM] Transitioning to state: {state_name}")
        self.current_state = state_name
        
        # Stop camera if running, it will be restarted by state if needed
        self.stop_camera()
        
        # Clean current view container
        for widget in self.view_container.winfo_children():
            widget.pack_forget()
            widget.grid_forget()
            
        if state_name == "SCANNING":
            self.render_scanning_state()
        elif state_name == "PROMPT_SECURE":
            self.render_prompt_secure_state()
        elif state_name == "SETUP_SECURE":
            self.render_setup_secure_state()
        elif state_name == "ACCESS_GATE":
            self.render_access_gate_state()
        elif state_name == "SECURE_EXPLORER":
            self.render_secure_explorer_state()

    def render_scanning_state(self):
        """State 1: No USB drive detected. Pulses scanner HUD."""
        self.set_status("● AWAITING STORAGE", "warning")
        
        frame = tk.Frame(self.view_container, bg=self.bg_panel, bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=50, pady=20)
        
        # Hologram Canvas
        scan_canvas = tk.Canvas(frame, bg=self.bg_well, bd=0, highlightthickness=0)
        scan_canvas.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Draw tech decorations
        w = 700
        h = 300
        scan_canvas.create_rectangle(10, 10, w, h, outline=self.accent_cyan, width=1, dash=(5, 5))
        scan_canvas.create_line(w//2 - 50, h//2, w//2 + 50, h//2, fill=self.accent_cyan, width=1)
        scan_canvas.create_line(w//2, h//2 - 50, w//2, h//2 + 50, fill=self.accent_cyan, width=1)
        scan_canvas.create_circle = lambda x, y, r, **kwargs: scan_canvas.create_oval(x-r, y-r, x+r, y+r, **kwargs)
        scan_canvas.create_circle(w//2, h//2, 80, outline=self.accent_cyan, width=1)
        scan_canvas.create_circle(w//2, h//2, 120, outline=self.accent_cyan, width=1, dash=(3, 9))
        
        scan_canvas.create_text(
            w//2, h//2 + 150, 
            text="[ STATUS: SEARCHING REMOVABLE INTERFACES... ]\nINSERT UNLOCKED OR SECURE PENDRIVE",
            fill=self.accent_cyan,
            font=("Courier New", 12, "bold"),
            justify=tk.CENTER
        )
        
        # Animate the scan grid
        def animate_grid():
            if self.current_state == "SCANNING":
                scan_canvas.delete("scanline")
                angle = (time.time() * 120) % 360
                rad_x = int(w//2 + 120 * math.cos(math.radians(angle)))
                rad_y = int(h//2 + 120 * math.sin(math.radians(angle)))
                scan_canvas.create_line(w//2, h//2, rad_x, rad_y, fill=self.accent_green, width=1, tags="scanline")
                scan_canvas.create_oval(rad_x-4, rad_y-4, rad_x+4, rad_y+4, fill=self.accent_green, outline="", tags="scanline")
                self.root.after(30, animate_grid)
        
        self.root.after(50, animate_grid)

    def render_prompt_secure_state(self):
        """State 2: Unsecured USB detected. Permission prompt to secure device."""
        self.set_status("● UNSECURED DEVICE DETECTED", "warning")
        
        frame = tk.Frame(self.view_container, bg=self.bg_panel, bd=1, relief="solid")
        frame.pack(fill="both", expand=True, padx=80, pady=40)
        
        # Tech icon/graphic
        icon_lbl = tk.Label(
            frame, 
            text="📂", 
            font=("Helvetica", 64), 
            fg=self.accent_amber, 
            bg=self.bg_panel
        )
        icon_lbl.pack(pady=(30, 10))
        
        drive_path = self.drive_var.get() or "Removable Volume"
        info_txt = f"STORAGE INTERFACE DETECTED AT:\n[{drive_path}]"
        
        path_lbl = tk.Label(
            frame, 
            text=info_txt, 
            font=("Courier New", 12, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel,
            justify=tk.CENTER
        )
        path_lbl.pack(pady=10)
        
        prompt_lbl = tk.Label(
            frame, 
            text="Aapka pendrive locked nahi hai.\nKya aap is drive par biometric encrypted vault initialize karna chahte hain?", 
            font=("Helvetica", 11, "bold"), 
            fg=self.text_white, 
            bg=self.bg_panel,
            justify=tk.CENTER
        )
        prompt_lbl.pack(pady=15)
        
        # Constraint note
        partition_note = tk.Label(
            frame,
            text="⚠️ Note: Is drive par koi naya partition nahi banaya jayega.\nSaari files ek hidden secure folder (.secure_vault/) ke andar lock ho jayengi.",
            font=("Helvetica", 9, "italic"),
            fg=self.text_dim,
            bg=self.bg_panel
        )
        partition_note.pack(pady=5)
        
        btn_frame = tk.Frame(frame, bg=self.bg_panel)
        btn_frame.pack(pady=20)
        
        btn_yes = tk.Button(
            btn_frame,
            text="[ YES, SECURE PENDRIVE ]",
            font=("Helvetica", 11, "bold"),
            bg="#143020",
            fg=self.accent_green,
            activebackground=self.accent_green,
            activeforeground=self.bg_dark,
            bd=0,
            padx=20,
            pady=10,
            command=lambda: self.set_state("SETUP_SECURE")
        )
        btn_yes.pack(side="left", padx=15)
        
        btn_no = tk.Button(
            btn_frame,
            text="[ NO, KEEP UNSECURED ]",
            font=("Helvetica", 11, "bold"),
            bg="#30141a",
            fg=self.accent_red,
            activebackground=self.accent_red,
            activeforeground=self.bg_dark,
            bd=0,
            padx=20,
            pady=10,
            command=lambda: self.log("User chose to keep drive unsecured. Awaiting authentication actions.")
        )
        btn_no.pack(side="right", padx=15)

    def render_setup_secure_state(self):
        """State 3: Setup view. Biometric face capture + PIN definition."""
        self.set_status("● VAULT SETUP WIZARD", "warning")
        
        # Main structure split in two panels
        left_panel = tk.LabelFrame(
            self.view_container,
            text=" BIOMETRIC RECORDING (FACE SCAN) ",
            font=("Courier New", 10, "bold"),
            fg=self.accent_cyan,
            bg=self.bg_panel,
            bd=1,
            relief="solid"
        )
        left_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Repack camera canvas
        self.cam_canvas.pack_forget()
        self.cam_canvas = tk.Canvas(left_panel, bg="#000000", bd=0, highlightthickness=0)
        self.cam_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        right_panel = tk.Frame(self.view_container, bg=self.bg_dark, width=360)
        right_panel.pack(side="right", fill="both", padx=10, pady=10)
        right_panel.pack_propagate(False)
        
        # Config params
        cfg_frame = tk.LabelFrame(
            right_panel,
            text=" VAULT CONFIGURATION ",
            font=("Courier New", 10, "bold"),
            fg=self.accent_cyan,
            bg=self.bg_panel,
            bd=1,
            relief="solid"
        )
        cfg_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Setup target drive display
        tk.Label(cfg_frame, text="Target Device:", font=("Helvetica", 9, "bold"), fg=self.text_dim, bg=self.bg_panel).pack(anchor="w", padx=15, pady=(10, 2))
        drive_path = self.drive_var.get() or "None Selected"
        tk.Label(cfg_frame, text=drive_path, font=("Courier New", 10, "bold"), fg=self.accent_cyan, bg=self.bg_panel).pack(anchor="w", padx=15, pady=(0, 10))
        
        # PIN Entry
        tk.Label(cfg_frame, text="Enter Security PIN (4-8 digits):", font=("Helvetica", 10, "bold"), fg=self.text_white, bg=self.bg_panel).pack(anchor="w", padx=15, pady=5)
        self.setup_pin_entry.pack_forget()
        self.setup_pin_entry = tk.Entry(
            cfg_frame, 
            show="*", 
            bg="#03030d", 
            fg=self.accent_amber, 
            bd=1, 
            relief="solid",
            insertbackground=self.accent_cyan, 
            font=("Helvetica", 14, "bold"), 
            justify="center",
            width=18
        )
        self.setup_pin_entry.pack(anchor="w", padx=15, pady=5)
        
        # Label Entry
        tk.Label(cfg_frame, text="Vault Identifier Label:", font=("Helvetica", 10, "bold"), fg=self.text_white, bg=self.bg_panel).pack(anchor="w", padx=15, pady=5)
        self.setup_label_entry.pack_forget()
        self.setup_label_entry = tk.Entry(
            cfg_frame, 
            bg="#03030d", 
            fg=self.accent_cyan, 
            bd=1, 
            relief="solid",
            insertbackground=self.accent_cyan, 
            font=("Helvetica", 11, "bold"), 
            justify="center",
            width=22
        )
        self.setup_label_entry.pack(anchor="w", padx=15, pady=5)
        self.setup_label_entry.delete(0, tk.END)
        self.setup_label_entry.insert(0, "SecureUSB")
        
        # Scan status labels
        self.enroll_status_lbl.pack_forget()
        self.enroll_status_lbl = tk.Label(
            cfg_frame, 
            text="Webcam scanning required for Face ID.", 
            font=("Helvetica", 9, "italic"), 
            fg=self.text_dim, 
            bg=self.bg_panel,
            wraplength=320,
            justify=tk.LEFT
        )
        self.enroll_status_lbl.pack(anchor="w", padx=15, pady=10)
        
        # Setup control buttons
        self.btn_enroll_face.pack_forget()
        self.btn_enroll_face = tk.Button(
            cfg_frame, 
            text="[ CAPTURE FACIAL SCAN ]", 
            command=self.start_face_enrollment, 
            bg="#143014", 
            fg=self.accent_green, 
            activebackground=self.accent_green, 
            activeforeground=self.bg_dark, 
            bd=0, 
            pady=8,
            font=("Helvetica", 9, "bold")
        )
        self.btn_enroll_face.pack(fill="x", padx=15, pady=5)
        
        self.btn_setup_vault.pack_forget()
        self.btn_setup_vault = tk.Button(
            right_panel, 
            text="[ SECURE DRIVE & ENCRYPT ]", 
            command=self.finalize_vault_setup, 
            bg=self.accent_cyan, 
            fg=self.bg_dark, 
            activebackground=self.accent_green, 
            activeforeground=self.bg_dark, 
            bd=0, 
            pady=12,
            font=("Helvetica", 10, "bold")
        )
        self.btn_setup_vault.pack(fill="x", side="bottom")
        
        # Start camera automatically to capture face ID
        self.start_camera()

    def render_access_gate_state(self):
        """State 4: Secured USB drive authentication gateway. Face ID viewfinder + PIN keypad + Unprotect option."""
        self.set_status("● LOCKED", "secure")
        
        # Left Panel: Camera Stream (webcam)
        cam_panel = tk.LabelFrame(
            self.view_container, 
            text=" BIOMETRIC SCANNER (FACE ID) ", 
            font=("Courier New", 10, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        cam_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.cam_canvas.pack_forget()
        self.cam_canvas = tk.Canvas(cam_panel, bg="#000000", bd=0, highlightthickness=0)
        self.cam_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Right Panel: PIN pad & Unprotect Control
        ctrl_panel = tk.Frame(self.view_container, bg=self.bg_dark, width=360)
        ctrl_panel.pack(side="right", fill="both", padx=10, pady=10)
        ctrl_panel.pack_propagate(False)
        
        # Keypad box
        pad_frame = tk.LabelFrame(
            ctrl_panel, 
            text=" ACCESS CONTROLLER ", 
            font=("Courier New", 10, "bold"), 
            fg=self.accent_cyan, 
            bg=self.bg_panel, 
            bd=1, 
            relief="solid"
        )
        pad_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # PIN Display
        self.pin_display = tk.Label(
            pad_frame, 
            textvariable=self.pin_display_var, 
            font=("Courier New", 16, "bold"), 
            bg=self.bg_well, 
            fg=self.accent_amber, 
            height=2, 
            relief="solid", 
            bd=1
        )
        self.pin_display.pack(fill="x", padx=15, pady=10)
        
        # Numeric keypad
        numpad_grid = tk.Frame(pad_frame, bg=self.bg_panel)
        numpad_grid.pack(expand=True, padx=10, pady=5)
        
        buttons = [
            '1', '2', '3',
            '4', '5', '6',
            '7', '8', '9',
            'CLEAR', '0', 'UNLOCK'
        ]
        
        for i, label in enumerate(buttons):
            row = i // 3
            col = i % 3
            
            btn_bg = "#101026"
            btn_fg = self.text_white
            if label == "CLEAR":
                btn_bg = "#260a12"
                btn_fg = self.accent_red
            elif label == "UNLOCK":
                btn_bg = "#0c2619"
                btn_fg = self.accent_green
                
            btn = tk.Button(
                numpad_grid, 
                text=label, 
                font=("Helvetica", 11, "bold"), 
                bg=btn_bg, 
                fg=btn_fg, 
                activebackground=self.accent_cyan, 
                activeforeground=self.bg_dark, 
                bd=0, 
                width=8, 
                height=2,
                command=lambda x=label: self.press_key(x)
            )
            btn.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            
        # Permanent Unprotect Option
        self.btn_unprotect_bottom = tk.Button(
            ctrl_panel,
            text="[ DECRYPT PERMANENTLY (UNPROTECT) ]",
            font=("Helvetica", 9, "bold"),
            bg="#260a12",
            fg=self.accent_red,
            activebackground=self.accent_red,
            activeforeground=self.bg_dark,
            bd=0,
            pady=12,
            command=self.controller.unprotect_drive_click
        )
        self.btn_unprotect_bottom.pack(fill="x", side="bottom")
        
        # Start camera automatically for biometric scan
        self.start_camera()

    def render_secure_explorer_state(self):
        """State 5: Unlocked secure file explorer view."""
        self.set_status("● SECURE VAULT DECRYPTED", "success")
        
        # 1. Sci-Fi Toolbar
        self.toolbar = tk.Frame(self.view_container, bg=self.bg_panel, height=45)
        self.toolbar.pack(fill="x", side="top", pady=(0, 5))
        self.toolbar.pack_propagate(False)
        
        btn_style = {"font": ("Helvetica", 8, "bold"), "bd": 0, "padx": 10, "pady": 4}
        
        btn_add_f = tk.Button(
            self.toolbar, text="➕ ADD FILE", bg="#0a261a", fg=self.accent_green,
            activebackground=self.accent_green, activeforeground=self.bg_dark,
            command=self.controller.add_file_click, **btn_style
        )
        btn_add_f.pack(side="left", padx=5, pady=5)
        
        btn_add_d = tk.Button(
            self.toolbar, text="📁 ADD FOLDER", bg="#0a261a", fg=self.accent_green,
            activebackground=self.accent_green, activeforeground=self.bg_dark,
            command=self.controller.add_folder_click, **btn_style
        )
        btn_add_d.pack(side="left", padx=5, pady=5)
        
        btn_ext = tk.Button(
            self.toolbar, text="💾 EXTRACT", bg="#0c202d", fg=self.accent_cyan,
            activebackground=self.accent_cyan, activeforeground=self.bg_dark,
            command=self.controller.extract_selected_click, **btn_style
        )
        btn_ext.pack(side="left", padx=5, pady=5)
        
        btn_del = tk.Button(
            self.toolbar, text="🗑️ SECURE SHRED", bg="#260a12", fg=self.accent_red,
            activebackground=self.accent_red, activeforeground=self.bg_dark,
            command=self.controller.delete_selected_click, **btn_style
        )
        btn_del.pack(side="left", padx=5, pady=5)
        
        btn_lock = tk.Button(
            self.toolbar, text="🔒 LOCK & EJECT", bg="#211708", fg=self.accent_amber,
            activebackground=self.accent_amber, activeforeground=self.bg_dark,
            command=self.controller.lock_drive_click, **btn_style
        )
        btn_lock.pack(side="right", padx=5, pady=5)
        
        # 2. Explorer Viewport Frame
        self.tree_frame = tk.Frame(self.view_container, bg=self.bg_dark)
        self.tree_frame.pack(fill="both", expand=True)
        
        # Repack treeview scrollbars & main treeview
        self.vsb.pack_forget()
        self.hsb.pack_forget()
        self.tree.pack_forget()
        
        self.vsb = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.hsb = ttk.Scrollbar(self.tree_frame, orient="horizontal", command=self.tree.xview)
        
        self.tree.config(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        
        self.vsb.pack(side="right", fill="y")
        self.hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        
        # 3. Explorer status bar
        self.stats_bar = tk.Frame(self.view_container, bg=self.bg_panel, height=20)
        self.stats_bar.pack(fill="x", side="bottom", pady=(5, 0))
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
            self.log(f"Manually selected USB mount: {dir_path}")

    def browse_setup_directory(self):
        self.browse_directory()

    def update_drives_dropdown(self, drives):
        """Called by main.py USB Watcher thread. Triggers layout state machine transitions."""
        self.drives_list = drives
        options = [f"{d['path']} ({d['size']}) - {d['model']}" for d in drives]
        
        self.drive_combo['values'] = options
        self.setup_drive_combo['values'] = options
        
        if drives:
            # Sync dropdown selection
            first_drive = drives[0]
            self.drive_var.set(options[0])
            self.setup_drive_var.set(options[0])
            
            # Transition states if not currently unlocked
            if not self.is_unlocked:
                # Let handle_drives_change in main.py determine if vault is initialized
                # it will call show_unlock_tab() or show_setup_tab()
                pass
        else:
            self.drive_var.set("")
            self.setup_drive_var.set("")
            if not self.is_unlocked:
                self.set_state("SCANNING")

    def show_unlock_tab(self):
        """Called by main.py. Transition to the biometric lock access gate."""
        if not self.is_unlocked:
            self.set_state("ACCESS_GATE")

    def show_setup_tab(self):
        """Called by main.py. Transition to the permission prompt view."""
        if not self.is_unlocked:
            self.set_state("PROMPT_SECURE")

    def show_vault_explorer(self, files_dict):
        """Called by main.py after key verification. Transition to file explorer."""
        self.is_unlocked = True
        self.set_state("SECURE_EXPLORER")
        self.populate_explorer(files_dict)

    def hide_vault_explorer(self):
        """Called by main.py when vault is locked."""
        self.is_unlocked = False
        self.entered_pin = ""
        self.pin_display_var.set("ENTER PIN")
        # Go back to gate if USB is still inserted, else scanning
        if self.drives_list:
            self.set_state("ACCESS_GATE")
        else:
            self.set_state("SCANNING")

    def format_size(self, size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def populate_explorer(self, files_dict):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        node_map = {}
        total_size = 0
        total_files = 0
        
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
            self.log(f"[FILE CONTROL] Requesting decrypt-and-read for: {rel_path}")
            self.controller.handle_open_file(rel_path)

    def on_tree_select(self, event):
        pass

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
            if self.pin_display_var.get() in ["ENTER PIN", "RETRY PIN"]:
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
        self.log("[AUTH GATEWAY] Initializing key verification...")
        self.controller.handle_unlock_request(self.entered_pin)

    def start_face_enrollment(self):
        pin = self.setup_pin_entry.get()
        if len(pin) < 4 or len(pin) > 8 or not pin.isdigit():
            messagebox.showerror("Error", "PIN must be between 4 and 8 digits!")
            return
        self.log("[BIOMETRIC RECORDER] Opening camera feed. Align face in targeting box...")
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
            self.log("[HARDWARE ALERT] Webcam not detected. Reverting to PIN fallback.")
            self.draw_no_camera()
            return
        self.is_camera_running = True
        self.log("[HARDWARE ENGAGED] Biometric video stream online.")
        self.update_camera_feed()

    def stop_camera(self):
        self.is_camera_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.cam_canvas.delete("all")

    def draw_no_camera(self):
        self.cam_canvas.delete("all")
        canvas_width = self.cam_canvas.winfo_width() or 400
        canvas_height = self.cam_canvas.winfo_height() or 300
        
        self.cam_canvas.create_rectangle(10, 10, canvas_width-10, canvas_height-10, fill="#04040d", outline=self.accent_amber, width=1)
        self.cam_canvas.create_text(
            canvas_width//2, canvas_height//2, 
            text="[ BIOMETRIC INTERFACE OFFLINE ]\n\nPIN Entry Fallback Mode Active.\nFacial Enrollment Disabled.", 
            fill=self.accent_amber, 
            font=("Courier New", 10, "bold"),
            justify=tk.CENTER
        )

    def update_camera_feed(self):
        if not self.is_camera_running or not self.cap or self.is_unlocked:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.root.after(15, self.update_camera_feed)
            return

        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape
        
        # Biometric target calculation
        gray_face, bbox, matching_info = self.controller.process_camera_frame(frame)
        
        # HUD overlays (Cyberpunk Sci-Fi HUD)
        border_color = (255, 240, 0) # BGR
        length = 25
        # Draw camera corners
        cv2.line(frame, (10, 10), (10 + length, 10), border_color, 1)
        cv2.line(frame, (10, 10), (10, 10 + length), border_color, 1)
        cv2.line(frame, (width - 10, 10), (width - 10 - length, 10), border_color, 1)
        cv2.line(frame, (width - 10, 10), (width - 10, 10 + length), border_color, 1)
        cv2.line(frame, (10, height - 10), (10 + length, height - 10), border_color, 1)
        cv2.line(frame, (10, height - 10), (10, height - 10 - length), border_color, 1)
        cv2.line(frame, (width - 10, height - 10), (width - 10 - length, height - 10), border_color, 1)
        cv2.line(frame, (width - 10, height - 10), (width - 10, height - 10 - length), border_color, 1)

        # Draw scanning radar
        radar_center = (width - 45, 45)
        radar_radius = 20
        cv2.circle(frame, radar_center, radar_radius, (80, 80, 80), 1)
        angle = int((time.time() * 200) % 360)
        radar_x = int(radar_center[0] + radar_radius * math.cos(math.radians(angle)))
        radar_y = int(radar_center[1] + radar_radius * math.sin(math.radians(angle)))
        cv2.line(frame, radar_center, (radar_x, radar_y), (0, 255, 102), 1)

        # Telemetry
        cv2.putText(frame, "SYS CORE: CRYPTOSHIELD v3.2", (20, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 240, 0), 1)
        cv2.putText(frame, "CIPHER: AES-256-GCM HARDWARE BYPASS DETECT", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 240, 0), 1)
        
        status_text = "STATUS: INITIALIZING"
        status_color = (0, 183, 255)
        
        if self.controller.face_auth.is_trained:
            if self.controller.face_match_status:
                status_text = "BIOMETRICS CONFIRMED"
                status_color = (102, 255, 0)
            else:
                status_text = "AWAITING BIO TARGET"
                status_color = (0, 0, 255)
        cv2.putText(frame, status_text, (20, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.35, status_color, 1)

        # Targeting Reticle
        if bbox is not None:
            x, y, w, h = bbox
            color = (102, 255, 0) if matching_info.get("match", False) else (0, 183, 255)
            
            t_len = 15
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
            cv2.line(frame, (cx - 5, cy), (cx + 5, cy), color, 1)
            cv2.line(frame, (cx, cy - 5), (cx, cy + 5), color, 1)
            
            cv2.putText(frame, "TARGET ENROLL LOCK", (x, y - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1)
            cv2.putText(frame, f"MATCH RATE: {matching_info.get('confidence', '')}", (x, y - 8), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
            
            if matching_info.get("verifying", False):
                pulsing_val = int((math.sin(time.time() * 10) + 1) * 127)
                cv2.putText(frame, "ANALYZING BIOMETRICS...", (30, height - 30), 
                            cv2.FONT_HERSHEY_COMPLEX, 0.45, (0, pulsing_val, 255), 1)
        else:
            cv2.putText(frame, "SCANNING FOR BIO SIGNATURE", (30, height - 30), 
                        cv2.FONT_HERSHEY_COMPLEX, 0.45, (120, 120, 120), 1)

        # Convert image to TK PhotoImage
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        
        canvas_width = self.cam_canvas.winfo_width() or 400
        canvas_height = self.cam_canvas.winfo_height() or 300
        
        if canvas_width > 10 and canvas_height > 10:
            img_pil = img_pil.resize((canvas_width, canvas_height), Image.Resampling.LANCZOS if hasattr(Image, 'LANCZOS') else Image.BICUBIC)
            
        self.webcam_canvas_image = ImageTk.PhotoImage(img_pil)
        self.cam_canvas.create_image(0, 0, anchor="nw", image=self.webcam_canvas_image)
        
        # Holographic sweep line
        scan_y = int((time.time() * 120) % canvas_height)
        self.cam_canvas.create_line(0, scan_y, canvas_width, scan_y, fill=self.accent_cyan, width=1, dash=(5, 3))
        
        self.root.after(15, self.update_camera_feed)
