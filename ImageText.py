
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from PIL import Image

# Unicode Braille-style characters ordered from light to dark.
GLYPHS = [
    "⠀", "⠁", "⠂", "⠄", "⠈", "⠐", "⠠",
    "⠃", "⠅", "⠉", "⠑", "⠡", "⠢", "⠤",
    "⠆", "⠒", "⠔", "⠖", "⠘", "⠊", "⠌",
    "⠜", "⠦", "⠧", "⠣", "⠩", "⠪", "⠫",
    "⠭", "⠮", "⠯", "⠰", "⠱", "⠲", "⠳",
    "⠴", "⠵", "⠶", "⠷", "⠸", "⠹", "⠺",
    "⠻", "⠼", "⠽", "⠾", "⠿",
    "⡀", "⡁", "⡂", "⡄", "⡈", "⡐", "⡠",
    "⡃", "⡇", "⡏", "⡟", "⡿",
    "⢀", "⢁", "⢂", "⢄", "⢈", "⢐", "⢠",
    "⢃", "⢇", "⢏", "⢟", "⢿",
    "⣀", "⣁", "⣂", "⣄", "⣈", "⣐", "⣠",
    "⣃", "⣇", "⣏", "⣟", "⣿"
]

BG = "#10131B"
PANEL = "#1A2030"
FG = "#EDF2F7"
MUTED = "#A5B0C2"
ACCENT = "#6D5DFC"
BLANK = "⠀"


class ImageTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ImageText - Unicode Dot Art")
        self.root.geometry("1000x750")
        self.root.minsize(700, 520)
        self.root.configure(bg=BG)

        self.image = None
        self.image_path = None
        self.art = ""

        header = tk.Frame(root, bg=BG)
        header.pack(fill="x", padx=20, pady=(16, 10))

        tk.Label(
            header,
            text="ImageText",
            font=("Segoe UI", 23, "bold"),
            bg=BG, fg=FG
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Turn images into recognizable Unicode dot art",
            font=("Segoe UI", 10),
            bg=BG, fg=MUTED
        ).pack(anchor="w", pady=(2, 0))

        file_panel = tk.Frame(root, bg=PANEL, padx=12, pady=12)
        file_panel.pack(fill="x", padx=16, pady=5)

        self.button(
            file_panel, "Open Image", self.open_image, ACCENT
        ).pack(side="left")

        self.filename = tk.Label(
            file_panel,
            text="No image selected",
            bg=PANEL, fg=MUTED,
            font=("Segoe UI", 10),
            anchor="w"
        )
        self.filename.pack(side="left", padx=12, fill="x", expand=True)

        settings = tk.Frame(root, bg=BG)
        settings.pack(fill="x", padx=20, pady=8)

        tk.Label(
            settings,
            text="Character width",
            bg=BG, fg=FG
        ).grid(row=0, column=0, sticky="w")

        self.width = tk.IntVar(value=250)

        tk.Scale(
            settings,
            from_=50,
            to=750,
            resolution=10,
            orient="horizontal",
            variable=self.width,
            command=self.on_setting_changed,
            bg=BG,
            fg=FG,
            troughcolor="#30384A",
            highlightthickness=0,
            length=350
        ).grid(row=0, column=1, padx=10, sticky="w")

        self.width_label = tk.Label(
            settings,
            text="250",
            bg=BG, fg=FG,
            font=("Segoe UI", 10, "bold")
        )
        self.width_label.grid(row=0, column=2, padx=5)

        tk.Label(
            settings,
            text="Contrast",
            bg=BG, fg=FG
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.contrast = tk.IntVar(value=135)

        tk.Scale(
            settings,
            from_=50,
            to=200,
            resolution=5,
            orient="horizontal",
            variable=self.contrast,
            command=self.on_setting_changed,
            bg=BG,
            fg=FG,
            troughcolor="#30384A",
            highlightthickness=0,
            length=350
        ).grid(row=1, column=1, padx=10, pady=(8, 0), sticky="w")

        self.transparent = tk.BooleanVar(value=True)

        tk.Checkbutton(
            settings,
            text="Keep transparent PNG background blank",
            variable=self.transparent,
            command=self.convert,
            bg=BG,
            fg=FG,
            selectcolor=PANEL,
            activebackground=BG,
            activeforeground=FG
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 0))

        preview_panel = tk.Frame(root, bg=PANEL, padx=2, pady=2)
        preview_panel.pack(
            fill="both", expand=True,
            padx=16, pady=(4, 8)
        )

        self.preview = tk.Text(
            preview_panel,
            bg="#080A0F",
            fg="#F3F4F6",
            insertbackground=FG,
            font=("Consolas", 10),
            wrap="none",
            relief="flat",
            padx=12,
            pady=12,
            undo=False
        )
        self.preview.pack(side="left", fill="both", expand=True)

        scrollbar_y = tk.Scrollbar(
            preview_panel,
            command=self.preview.yview
        )
        scrollbar_y.pack(side="right", fill="y")

        scrollbar_x = tk.Scrollbar(
            root,
            orient="horizontal",
            command=self.preview.xview
        )
        scrollbar_x.pack(fill="x", padx=16)

        self.preview.configure(
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            state="disabled"
        )

        self.show_preview("Open an image to generate your dot art.")

        actions = tk.Frame(root, bg=BG)
        actions.pack(fill="x", padx=16, pady=12)

        self.button(
            actions, "Generate", self.convert, "#334155"
        ).pack(side="left", padx=(0, 6))

        self.button(
            actions, "Copy Art", self.copy_art, "#4F46E5"
        ).pack(side="left", padx=6)

        self.button(
            actions, "Save TXT", self.save_art, "#087F5B"
        ).pack(side="left", padx=6)

        self.status = tk.Label(
            actions,
            text="Ready",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9)
        )
        self.status.pack(side="right")

    def button(self, parent, text, command, color):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            borderwidth=0,
            padx=16,
            pady=9,
            cursor="hand2"
        )

    def on_setting_changed(self, _value=None):
        self.width_label.configure(text=str(self.width.get()))
        self.convert()

    def show_preview(self, text):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", text)
        self.preview.configure(state="disabled")

    def open_image(self):
        path = filedialog.askopenfilename(
            title="Choose an image",
            filetypes=[
                (
                    "Image files",
                    "*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff"
                ),
                ("All files", "*.*")
            ]
        )

        if not path:
            return

        try:
            new_image = Image.open(path)
            new_image.load()

            self.image = new_image.convert("RGBA")
            self.image_path = Path(path)

            self.filename.configure(text=self.image_path.name)
            self.convert()

        except Exception as error:
            messagebox.showerror("Image Error", str(error))

    def convert(self, *_args):
        if self.image is None:
            return

        try:
            width = self.width.get()
            original_width, original_height = self.image.size

            if original_width <= 0 or original_height <= 0:
                return

            # Unicode characters are taller than they are wide.
            height = max(
                1,
                round(width * original_height / original_width * 0.48)
            )

            image = self.image.resize(
                (width, height),
                Image.Resampling.LANCZOS
            )

            pixels = list(image.getdata())
            rows = []
            contrast = self.contrast.get() / 100.0

            for y in range(height):
                row = []

                for x in range(width):
                    r, g, b, a = pixels[y * width + x]

                    if self.transparent.get() and a < 32:
                        row.append(BLANK)
                        continue

                    # Composite semi-transparent pixels onto white.
                    if a < 255:
                        r = round(r * a / 255 + 255 * (255 - a) / 255)
                        g = round(g * a / 255 + 255 * (255 - a) / 255)
                        b = round(b * a / 255 + 255 * (255 - a) / 255)

                    brightness = (
                        0.2126 * r +
                        0.7152 * g +
                        0.0722 * b
                    )

                    brightness = 128 + (brightness - 128) * contrast
                    brightness = max(0, min(255, brightness))

                    # Leave white regions empty.
                    if brightness >= 242:
                        row.append(BLANK)
                    else:
                        darkness = (255 - brightness) / 255.0
                        index = round(darkness * (len(GLYPHS) - 1))
                        row.append(GLYPHS[index])

                rows.append("".join(row))

            self.art = "\n".join(rows)
            self.show_preview(self.art)

            self.status.configure(
                text=f"{width} × {height} characters"
            )

        except Exception as error:
            messagebox.showerror("Conversion Error", str(error))

    def copy_art(self):
        if not self.art:
            messagebox.showinfo("No Art", "Open an image first.")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.art)
            self.root.update()
            self.status.configure(text="Copied!")
        except Exception as error:
            messagebox.showerror("Clipboard Error", str(error))

    def save_art(self):
        if not self.art:
            messagebox.showinfo("No Art", "Open an image first.")
            return

        default_name = (
            self.image_path.stem + "_dot_art.txt"
            if self.image_path else "dot_art.txt"
        )

        path = filedialog.asksaveasfilename(
            title="Save dot art",
            defaultextension=".txt",
            initialfile=default_name,
            filetypes=[("Text files", "*.txt")]
        )

        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as file:
                file.write(self.art)

            self.status.configure(text="Saved!")
            messagebox.showinfo(
                "Saved",
                "Your dot art was saved successfully."
            )

        except Exception as error:
            messagebox.showerror("Save Error", str(error))


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageTextApp(root)
    root.mainloop()
