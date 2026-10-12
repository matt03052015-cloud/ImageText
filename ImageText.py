import tkinter as tk
import random
import json
import threading
import urllib.request
import urllib.error

from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageOps, ImageFilter

BG = "#10131B"
PANEL = "#1A2030"
PANEL2 = "#222B3D"
FG = "#EDF2F7"
MUTED = "#A5B0C2"
ACCENT = "#7667FF"
BORDER = "#30394D"
PV_BG = "#080A0F"
PV_FG = "#F3F4F6"

GITHUB_API = (
    "https://api.github.com/repos/"
    "matt03052015-cloud/ImageText/releases/latest"
)
GITHUB_RELEASE_PAGE = (
    "https://github.com/matt03052015-cloud/ImageText/releases/latest"
)

DOTS = [
    (0, 0, 1), (0, 1, 2), (0, 2, 4), (0, 3, 64),
    (1, 0, 8), (1, 1, 16), (1, 2, 32), (1, 3, 128)
]

CODE_OPTIONS = [
    ("§0 — Black", "§0", {"color": "#000000"}),
    ("§1 — Dark Blue", "§1", {"color": "#0000AA"}),
    ("§2 — Dark Green", "§2", {"color": "#00AA00"}),
    ("§3 — Dark Aqua", "§3", {"color": "#00AAAA"}),
    ("§4 — Dark Red", "§4", {"color": "#AA0000"}),
    ("§5 — Dark Purple", "§5", {"color": "#AA00AA"}),
    ("§6 — Gold", "§6", {"color": "#FFAA00"}),
    ("§7 — Gray", "§7", {"color": "#AAAAAA"}),
    ("§8 — Dark Gray", "§8", {"color": "#555555"}),
    ("§9 — Blue", "§9", {"color": "#5555FF"}),
    ("§a — Green", "§a", {"color": "#55FF55"}),
    ("§b — Aqua", "§b", {"color": "#55FFFF"}),
    ("§c — Red", "§c", {"color": "#FF5555"}),
    ("§d — Light Purple", "§d", {"color": "#FF55FF"}),
    ("§e — Yellow", "§e", {"color": "#FFFF55"}),
    ("§f — White", "§f", {"color": "#FFFFFF"}),

    # Additional Bedrock material / coin codes
    ("§g — Minecoin Gold", "§g", {"color": "#FFAA00"}),
    ("§h — Material Quartz", "§h", {"color": "#FFFFFF"}),
    ("§i — Material Iron", "§i", {"color": "#C0C0C0"}),
    ("§j — Material Netherite", "§j", {"color": "#3B3B3B"}),
    ("§m — Material Redstone", "§m", {"color": "#FF0000"}),
    ("§n — Material Copper", "§n", {"color": "#B87333"}),

    # Formatting codes
    ("§k — Obfuscated", "§k", {"format": "obfuscate"}),
    ("§l — Bold", "§l", {"format": "bold"}),
    ("§m — Strikethrough", "§m", {"format": "strike"}),
    ("§n — Underlined", "§n", {"format": "underline"}),
    ("§o — Italic", "§o", {"format": "italic"}),
    ("§r — Reset", "§r", {"color": PV_FG}),
]

OB_CHARS = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789!@#$%^&*()_+-=[]{}|;:,.<>/?"
)


def threshold_art(
    image, width, mode, threshold,
    sensitivity, thickness, transparent
):
    image = ImageOps.exif_transpose(image).convert("RGBA")
    original_w, original_h = image.size

    cols = max(1, int(width))
    rows = max(1, round(cols * original_h / original_w * 0.5))
    target_size = (cols * 2, rows * 4)

    alpha = image.getchannel("A").resize(
        target_size, Image.Resampling.LANCZOS
    )

    rgb = Image.new("RGB", image.size, "white")
    rgb.paste(image.convert("RGB"), mask=image.getchannel("A"))

    gray = ImageOps.grayscale(rgb).resize(
        target_size, Image.Resampling.LANCZOS
    )

    cutoff = int(threshold)

    if mode == "Convert to Line Art":
        edges = gray.filter(ImageFilter.FIND_EDGES)
        line_mask = ImageOps.invert(edges)

        cutoff = int(
            5 + max(0.0, min(1.0, float(sensitivity))) * 250
        )

        thickness = max(0, min(4, int(thickness)))

        if thickness:
            line_mask = line_mask.filter(
                ImageFilter.MinFilter(2 * thickness + 1)
            )

        gray = line_mask

    elif mode == "Dither (shading)":
        shift = 128 - int(threshold)
        gray = gray.point(
            lambda p: max(0, min(255, p + shift))
        )
        gray = gray.convert("1").convert("L")

    pixels = gray.load()
    alpha_pixels = alpha.load()
    result = []

    for cy in range(rows):
        line = []

        for cx in range(cols):
            bits = 0

            for dx, dy, bit in DOTS:
                x = cx * 2 + dx
                y = cy * 4 + dy

                if transparent and alpha_pixels[x, y] < 32:
                    continue

                value = pixels[x, y]

                if mode == "Convert to Line Art":
                    on = value < cutoff
                elif mode == "Dither (shading)":
                    on = value < 128
                else:
                    on = value < int(threshold)

                if on:
                    bits |= bit

            line.append(chr(0x2800 + bits))

        result.append(
            "".join(line).rstrip()
            if transparent
            else "".join(line)
        )

    return "\n".join(result), rows


class ImageTextApp:
    def __init__(self, root):
        self.root = root
        root.title("ImageText — Unicode Dot Art")
        root.geometry("1180x790")
        root.minsize(760, 540)
        root.configure(bg=BG)

        self.image = None
        self.image_path = None
        self.art = ""
        self._after_id = None
        self._changelog_loading = False

        self.mode = tk.StringVar(value="Auto")
        self.width = tk.IntVar(value=180)
        self.threshold = tk.IntVar(value=128)
        self.sensitivity = tk.DoubleVar(value=0.45)
        self.thickness = tk.IntVar(value=1)
        self.transparent = tk.BooleanVar(value=True)
        self.code_label = tk.StringVar(value="§f — White")

        self.status = tk.StringVar(
            value="Open an image to begin."
        )

        self._style()
        self._ui()

        root.bind("<Control-o>", lambda e: self.open_image())
        root.bind("<Control-s>", lambda e: self.save_art())
        root.bind("<Control-Shift-c>", lambda e: self.copy_art())

    def _style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "TCombobox",
            fieldbackground=PANEL2,
            background=PANEL2,
            foreground=FG,
            arrowcolor=FG
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", PANEL2)],
            foreground=[("readonly", FG)]
        )
        style.configure(
            "Horizontal.TScale",
            background=PANEL,
            troughcolor=PANEL2
        )
        style.configure(
            "TCheckbutton",
            background=PANEL,
            foreground=FG
        )
        style.map(
            "TCheckbutton",
            background=[("active", PANEL)],
            foreground=[("active", FG)]
        )

    def _ui(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=20, pady=(15, 12))

        titlebox = tk.Frame(header, bg=BG)
        titlebox.pack(side="left", fill="x", expand=True)

        tk.Label(
            titlebox,
            text="ImageText",
            bg=BG,
            fg=FG,
            font=("Segoe UI", 23, "bold")
        ).pack(anchor="w")

        tk.Label(
            titlebox,
            text="Convert pictures into Unicode Braille dot art",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(2, 0))

        self._button(
            header, "＋  Open Image",
            self.open_image, ACCENT
        ).pack(side="right")

        main = tk.Frame(self.root, bg=BG)
        main.pack(
            fill="both", expand=True,
            padx=20, pady=(0, 10)
        )

        main.grid_columnconfigure(0, minsize=245, weight=0)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        # Scrollable Settings container
        side = tk.Frame(
            main, bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        side.grid(
            row=0, column=0,
            sticky="nsew", padx=(0, 14)
        )
        side.grid_rowconfigure(0, weight=1)
        side.grid_columnconfigure(0, weight=1)

        self.settings_canvas = tk.Canvas(
            side, bg=PANEL, highlightthickness=0,
            borderwidth=0
        )
        self.settings_scrollbar = ttk.Scrollbar(
            side, orient="vertical",
            command=self.settings_canvas.yview
        )
        self.settings_canvas.configure(
            yscrollcommand=self.settings_scrollbar.set
        )

        self.settings_canvas.grid(
            row=0, column=0, sticky="nsew"
        )
        self.settings_scrollbar.grid(
            row=0, column=1, sticky="ns"
        )

        self.settings_inner = tk.Frame(
            self.settings_canvas, bg=PANEL
        )
        self.settings_window = self.settings_canvas.create_window(
            (0, 0), window=self.settings_inner, anchor="nw"
        )

        self.settings_inner.bind(
            "<Configure>", self._update_settings_scroll
        )
        self.settings_canvas.bind(
            "<Configure>", self._resize_settings_inner
        )

        self.settings_canvas.bind(
            "<Enter>", self._bind_settings_wheel
        )
        self.settings_canvas.bind(
            "<Leave>", self._unbind_settings_wheel
        )

        self._build_settings()

        # Preview
        right = tk.Frame(main, bg=BG)
        right.grid(row=0, column=1, sticky="nsew")
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        top = tk.Frame(right, bg=BG)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        tk.Label(
            top, text="DOT ART PREVIEW",
            bg=BG, fg=FG,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        self.count = tk.Label(
            top, text="0 characters",
            bg=BG, fg=MUTED,
            font=("Segoe UI", 9)
        )
        self.count.pack(side="right")

        art_panel = tk.Frame(
            right, bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        art_panel.grid(row=1, column=0, sticky="nsew")
        art_panel.grid_rowconfigure(0, weight=1)
        art_panel.grid_columnconfigure(0, weight=1)

        self.preview = tk.Text(
            art_panel,
            bg=PV_BG,
            fg=PV_FG,
            insertbackground=FG,
            selectbackground="#454078",
            font=("Consolas", 9),
            wrap="none",
            relief="flat",
            padx=14,
            pady=14,
            undo=False
        )

        sy = ttk.Scrollbar(
            art_panel, orient="vertical",
            command=self.preview.yview
        )
        sx = ttk.Scrollbar(
            art_panel, orient="horizontal",
            command=self.preview.xview
        )

        self.preview.configure(
            yscrollcommand=sy.set,
            xscrollcommand=sx.set
        )

        self.preview.grid(row=0, column=0, sticky="nsew")
        sy.grid(row=0, column=1, sticky="ns")
        sx.grid(row=1, column=0, sticky="ew")

        self.preview.insert(
            "1.0", "Open an image to generate Braille dot art."
        )
        self.preview.configure(state="disabled")

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=20, pady=(0, 12))

        tk.Label(
            footer,
            textvariable=self.status,
            bg=BG, fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        tk.Label(
            footer,
            text="Ctrl+O open  •  Ctrl+S save",
            bg=BG, fg="#65728A",
            font=("Segoe UI", 9)
        ).pack(side="right")

    def _build_settings(self):
        side = self.settings_inner

        tk.Label(
            side, text="SETTINGS",
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=0, column=0, sticky="w",
            padx=16, pady=(16, 12)
        )

        self.file_label = tk.Label(
            side, text="No image selected",
            bg=PANEL, fg=FG,
            font=("Segoe UI", 10, "bold"),
            wraplength=220, anchor="w",
            justify="left"
        )
        self.file_label.grid(
            row=1, column=0, sticky="ew",
            padx=16, pady=(0, 12)
        )

        self._label(side, "MODE", 2)

        self.mode_box = ttk.Combobox(
            side, textvariable=self.mode,
            values=[
                "Auto",
                "Convert to Line Art",
                "Dither (shading)"
            ],
            state="readonly"
        )
        self.mode_box.grid(
            row=3, column=0, sticky="ew",
            padx=16, pady=(0, 4)
        )
        self.mode_box.bind(
            "<<ComboboxSelected>>", self._schedule_convert
        )

        tk.Label(
            side,
            text="Choose how the image is processed.",
            bg=PANEL, fg=MUTED,
            wraplength=220, justify="left",
            font=("Segoe UI", 8)
        ).grid(
            row=4, column=0, sticky="w",
            padx=16, pady=(2, 8)
        )

        # Color and formatting picker
        self._label(side, "COLOR / FORMAT CODE", 5)

        self.code_box = ttk.Combobox(
            side,
            textvariable=self.code_label,
            values=[option[0] for option in CODE_OPTIONS],
            state="readonly"
        )
        self.code_box.grid(
            row=6, column=0, sticky="ew",
            padx=16, pady=(0, 4)
        )
        self.code_box.bind(
            "<<ComboboxSelected>>", self._on_code_change
        )

        tk.Label(
            side,
            text=(
                "Preview applies the selected color or formatting. "
                "Copy and Save add its § code to every line."
            ),
            bg=PANEL, fg=MUTED,
            wraplength=220, justify="left",
            font=("Segoe UI", 8)
        ).grid(
            row=7, column=0, sticky="w",
            padx=16, pady=(2, 8)
        )

        self._label(side, "RESOLUTION", 8)
        self._slider(
            side, 9, self.width, 10, 360, 5,
            "width", "Smaller", "More detailed"
        )

        self._label(side, "THRESHOLD / DARKNESS", 10)
        self._slider(
            side, 11, self.threshold, 20, 235, 5,
            "threshold", "Darker", "Lighter"
        )

        self._label(side, "LINE SENSITIVITY", 12)
        self._slider(
            side, 13, self.sensitivity, 0.0, 1.0, 0.05,
            "sensitivity", "Fewer lines", "More lines"
        )

        self._label(side, "LINE THICKNESS", 14)
        self._slider(
            side, 15, self.thickness, 0, 4, 1,
            "thickness", "Thinner", "Thicker"
        )

        ttk.Checkbutton(
            side,
            text="Keep transparent pixels blank",
            variable=self.transparent,
            command=self._schedule_convert
        ).grid(
            row=16, column=0, sticky="w",
            padx=16, pady=(12, 8)
        )

        tk.Label(
            side,
            text=(
                "Line controls work in Line Art mode. "
                "Dither creates stippled shading."
            ),
            bg=PANEL, fg=MUTED,
            wraplength=220, justify="left",
            font=("Segoe UI", 8)
        ).grid(
            row=17, column=0, sticky="w",
            padx=16, pady=(0, 12)
        )

        tk.Frame(side, bg=BORDER, height=1).grid(
            row=18, column=0, sticky="ew",
            padx=16, pady=3
        )

        actions = tk.Frame(side, bg=PANEL)
        actions.grid(
            row=19, column=0, sticky="ew",
            padx=16, pady=12
        )
        actions.grid_columnconfigure((0, 1), weight=1)

        self._button(
            actions, "Reset Settings",
            self.reset, "#334155"
        ).grid(
            row=0, column=0, columnspan=2,
            sticky="ew", pady=3
        )

        self._button(
            actions, "Copy Art",
            self.copy_art, ACCENT
        ).grid(
            row=1, column=0, sticky="ew",
            padx=(0, 4), pady=3
        )

        self._button(
            actions, "Save TXT",
            self.save_art, "#087F5B"
        ).grid(
            row=1, column=1, sticky="ew",
            padx=(4, 0), pady=3
        )

        self._button(
            actions, "View Changelog",
            self.show_changelog, "#475569"
        ).grid(
            row=2, column=0, columnspan=2,
            sticky="ew", pady=3
        )

    # ---------- Settings scrolling ----------

    def _update_settings_scroll(self, _event=None):
        self.settings_canvas.configure(
            scrollregion=self.settings_canvas.bbox("all")
        )

    def _resize_settings_inner(self, event):
        self.settings_canvas.itemconfigure(
            self.settings_window, width=event.width
        )

    def _bind_settings_wheel(self, _event=None):
        self.root.bind_all(
            "<MouseWheel>", self._settings_mousewheel
        )
        self.root.bind_all(
            "<Button-4>", self._settings_mousewheel_linux
        )
        self.root.bind_all(
            "<Button-5>", self._settings_mousewheel_linux
        )

    def _unbind_settings_wheel(self, _event=None):
        self.root.unbind_all("<MouseWheel>")
        self.root.unbind_all("<Button-4>")
        self.root.unbind_all("<Button-5>")

    def _settings_mousewheel(self, event):
        self.settings_canvas.yview_scroll(
            int(-event.delta / 120), "units"
        )

    def _settings_mousewheel_linux(self, event):
        if event.num == 4:
            self.settings_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.settings_canvas.yview_scroll(1, "units")

    # ---------- UI helpers ----------

    def _label(self, parent, text, row):
        tk.Label(
            parent, text=text,
            bg=PANEL, fg=FG,
            font=("Segoe UI", 9, "bold")
        ).grid(
            row=row, column=0, sticky="w",
            padx=16, pady=(7, 2)
        )

    def _slider(
        self, parent, row, var, low, high,
        resolution, key, left, right
    ):
        wrap = tk.Frame(parent, bg=PANEL)
        wrap.grid(
            row=row, column=0, sticky="ew",
            padx=16
        )
        wrap.grid_columnconfigure(0, weight=1)

        scale = tk.Scale(
            wrap,
            from_=low,
            to=high,
            resolution=resolution,
            orient="horizontal",
            variable=var,
            command=lambda _v: self._schedule_convert(),
            bg=PANEL,
            fg=FG,
            troughcolor=PANEL2,
            activebackground=ACCENT,
            highlightthickness=0,
            bd=0,
            showvalue=True
        )
        scale.grid(row=0, column=0, sticky="ew")

        tk.Label(
            wrap, text=left,
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8)
        ).grid(row=1, column=0, sticky="w")

        tk.Label(
            wrap, text=right,
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8)
        ).grid(row=1, column=0, sticky="e")

    def _button(self, parent, text, command, color):
        return tk.Button(
            parent, text=text,
            command=command,
            bg=color, fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat", bd=0,
            padx=13, pady=9,
            cursor="hand2",
            font=("Segoe UI", 9, "bold")
        )

    # ---------- Color and formatting ----------

    def _get_code_spec(self):
        label = self.code_label.get()

        for option_label, code, spec in CODE_OPTIONS:
            if option_label == label:
                return code, spec

        return "§f", {"color": "#FFFFFF"}

    def _on_code_change(self, *_):
        if self.art:
            self._render()

    def _obfuscate(self, text):
        return "".join(
            random.choice(OB_CHARS) if char != " " else " "
            for char in text
        )

    def _render(self):
        if not self.art:
            return

        _code, spec = self._get_code_spec()
        text = self.art

        if spec.get("format") == "obfuscate":
            text = self._obfuscate(self.art)

        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)

        tag = "selected_format"

        self.preview.tag_configure(
            tag,
            foreground=PV_FG,
            font=("Consolas", 9),
            underline=False,
            overstrike=False
        )

        if spec.get("color"):
            self.preview.tag_configure(
                tag, foreground=spec["color"]
            )

        fmt = spec.get("format")

        if fmt == "bold":
            self.preview.tag_configure(
                tag, font=("Consolas", 9, "bold")
            )
        elif fmt == "italic":
            self.preview.tag_configure(
                tag, font=("Consolas", 9, "italic")
            )
        elif fmt == "underline":
            self.preview.tag_configure(
                tag, underline=True
            )
        elif fmt == "strike":
            self.preview.tag_configure(
                tag, overstrike=True
            )

        self.preview.tag_add(tag, "1.0", "end")
        self.preview.configure(state="disabled")

    def _art_with_code(self):
        code, _spec = self._get_code_spec()

        # Prefix the selected code on every output line.
        return "\n".join(
            code + line for line in self.art.split("\n")
        )

    # ---------- Conversion ----------

    def _schedule_convert(self, *_):
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None

        if self.image is not None:
            self._after_id = self.root.after(
                140, self.convert
            )

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[
                (
                    "Image files",
                    "*.png *.jpg *.jpeg *.webp *.bmp "
                    "*.gif *.tif *.tiff"
                ),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        try:
            im = Image.open(path)
            im.load()

            self.image = im.convert("RGBA")
            self.image_path = Path(path)

            self.file_label.configure(
                text=self.image_path.name
            )

            self.status.set(
                f"Loaded {im.width} × {im.height} image"
            )

            self.convert()

        except Exception as error:
            messagebox.showerror("Image Error", str(error))

    def convert(self, *_):
        self._after_id = None

        if self.image is None:
            return

        try:
            self.art, rows = threshold_art(
                self.image,
                self.width.get(),
                self.mode.get(),
                self.threshold.get(),
                float(self.sensitivity.get()),
                self.thickness.get(),
                self.transparent.get()
            )

            self._render()

            self.count.configure(
                text=f"{len(self.art):,} characters"
            )

            self.status.set(
                f"{self.mode.get()}  •  "
                f"{self.width.get()} columns × {rows} lines"
            )

        except Exception as error:
            messagebox.showerror(
                "Conversion Error", str(error)
            )

    # ---------- GitHub changelog ----------

    def show_changelog(self):
        win = tk.Toplevel(self.root)
        win.title("ImageText — Changelog")
        win.geometry("700x570")
        win.minsize(480, 350)
        win.configure(bg=BG)
        win.transient(self.root)

        tk.Label(
            win, text="CHANGELOG",
            bg=BG, fg=FG,
            font=("Segoe UI", 17, "bold")
        ).pack(anchor="w", padx=20, pady=(18, 8))

        status = tk.StringVar(
            value="Fetching the latest GitHub release..."
        )

        tk.Label(
            win, textvariable=status,
            bg=BG, fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w"
        ).pack(fill="x", padx=20, pady=(0, 8))

        text_frame = tk.Frame(win, bg=PV_BG)
        text_frame.pack(
            fill="both", expand=True,
            padx=20, pady=(0, 12)
        )
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        box = tk.Text(
            text_frame,
            bg=PV_BG, fg=FG,
            insertbackground=FG,
            font=("Consolas", 10),
            wrap="word", relief="flat",
            padx=14, pady=12
        )

        scrollbar = ttk.Scrollbar(
            text_frame, orient="vertical",
            command=box.yview
        )
        box.configure(yscrollcommand=scrollbar.set)
        box.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        box.insert(
            "1.0",
            "Loading release information from GitHub..."
        )
        box.configure(state="disabled")

        def display(content):
            if not win.winfo_exists():
                return

            box.configure(state="normal")
            box.delete("1.0", "end")
            box.insert("1.0", content)
            box.configure(state="disabled")

        def fetch_release():
            try:
                request = urllib.request.Request(
                    GITHUB_API,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "ImageText-App"
                    }
                )

                with urllib.request.urlopen(
                    request, timeout=10
                ) as response:
                    data = json.loads(
                        response.read().decode("utf-8")
                    )

                if data.get("message"):
                    raise RuntimeError(data["message"])

                name = data.get("name") or "Latest Release"
                tag = data.get("tag_name") or "No version tag"
                body = data.get("body") or (
                    "This release does not contain release notes."
                )
                published = data.get("published_at") or "Unknown"
                url = data.get("html_url") or GITHUB_RELEASE_PAGE

                try:
                    date = datetime.fromisoformat(
                        published.replace("Z", "+00:00")
                    ).strftime("%Y-%m-%d %H:%M UTC")
                except (ValueError, TypeError):
                    date = published

                content = (
                    f"{name}\n"
                    f"Version: {tag}\n"
                    f"Published: {date}\n"
                    f"Release page: {url}\n\n"
                    f"{body}"
                )

                self.root.after(
                    0,
                    lambda: (
                        status.set(f"Loaded release {tag}"),
                        display(content)
                    )
                )

            except Exception as error:
                content = (
                    "Unable to fetch the latest release notes.\n\n"
                    f"Reason: {error}\n\n"
                    "Check your internet connection, or open the "
                    "GitHub release page directly:\n"
                    f"{GITHUB_RELEASE_PAGE}\n\n"
                    "Image conversion still works offline."
                )

                self.root.after(
                    0,
                    lambda: (
                        status.set("Could not load GitHub release"),
                        display(content)
                    )
                )

        threading.Thread(
            target=fetch_release,
            daemon=True
        ).start()

        buttons = tk.Frame(win, bg=BG)
        buttons.pack(
            fill="x", padx=20, pady=(0, 16)
        )

        self._button(
            buttons, "Open GitHub Release",
            lambda: self._open_release_page(),
            "#334155"
        ).pack(side="left")

        self._button(
            buttons, "Close", win.destroy, ACCENT
        ).pack(side="right")

    def _open_release_page(self):
        import webbrowser
        webbrowser.open(GITHUB_RELEASE_PAGE)

    # ---------- Reset / copy / save ----------

    def reset(self):
        self.mode.set("Auto")
        self.width.set(180)
        self.threshold.set(128)
        self.sensitivity.set(0.45)
        self.thickness.set(1)
        self.transparent.set(True)
        self.code_label.set("§f — White")

        if self.image is not None:
            self.convert()
        else:
            self.status.set("Settings reset.")

    def copy_art(self):
        if not self.art:
            messagebox.showinfo(
                "No Art", "Open an image first."
            )
            return

        try:
            output = self._art_with_code()

            self.root.clipboard_clear()
            self.root.clipboard_append(output)
            self.root.update()

            code, _spec = self._get_code_spec()
            self.status.set(
                f"Art copied with {code} prefix."
            )

        except Exception as error:
            messagebox.showerror(
                "Clipboard Error", str(error)
            )

    def save_art(self):
        if not self.art:
            messagebox.showinfo(
                "No Art", "Open an image first."
            )
            return

        default = (
            self.image_path.stem
            if self.image_path
            else "image"
        ) + "_dot_art.txt"

        path = filedialog.asksaveasfilename(
            title="Save dot art",
            defaultextension=".txt",
            initialfile=default,
            filetypes=[("Text files", "*.txt")]
        )

        if not path:
            return

        try:
            Path(path).write_text(
                self._art_with_code(),
                encoding="utf-8"
            )

            self.status.set(
                f"Saved {Path(path).name}"
            )

        except Exception as error:
            messagebox.showerror(
                "Save Error", str(error)
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageTextApp(root)
    root.mainloop()
