"""ImageText - Unicode Braille Dot Art Converter
Install: py -m pip install pillow
Run:     py ImageText.py
"""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageEnhance

BG = '#10131B'; PANEL = '#1A2030'; PANEL2 = '#222B3D'; FG = '#EDF2F7'
MUTED = '#A5B0C2'; ACCENT = '#7667FF'; BORDER = '#30394D'; BLANK = '\u2800'
# Standard Unicode Braille dot layout: 2 columns x 4 rows.
DOTS = [(0,0,1),(0,1,2),(0,2,4),(0,3,64),(1,0,8),(1,1,16),(1,2,32),(1,3,128)]


def threshold_art(image, width, mode, threshold, sensitivity, thickness, transparent):
    image = ImageOps.exif_transpose(image).convert('RGBA')
    original_w, original_h = image.size
    # Each Braille character represents a 2 x 4 pixel block.
    cols = max(1, int(width))
    rows = max(1, round(cols * original_h / original_w * 0.5))
    target_size = (cols * 2, rows * 4)
    alpha = image.getchannel('A').resize(target_size, Image.Resampling.LANCZOS)
    rgb = Image.new('RGB', image.size, 'white')
    rgb.paste(image.convert('RGB'), mask=image.getchannel('A'))
    gray = ImageOps.grayscale(rgb).resize(target_size, Image.Resampling.LANCZOS)

    # Build a mode-specific grayscale image. Lower values become Braille dots.
    if mode == 'Convert to Line Art':
        edges = gray.filter(ImageFilter.FIND_EDGES)
        line_mask = ImageOps.invert(edges)
        # Sensitivity raises the cutoff: higher settings include weaker edges.
        cutoff = int(5 + max(0.0, min(1.0, float(sensitivity))) * 250)
        # MinFilter expands dark strokes, so thickness actually makes lines bolder.
        thickness = max(0, min(4, int(thickness)))
        if thickness:
            line_mask = line_mask.filter(ImageFilter.MinFilter(2 * thickness + 1))
        gray = line_mask
    elif mode == 'Dither (shading)':
        # Shift the grayscale before Pillow's Floyd–Steinberg dithering.
        # A higher threshold makes the final picture darker/more dotted.
        shift = 128 - int(threshold)
        gray = gray.point(lambda p: max(0, min(255, p + shift)))
        gray = gray.convert('1').convert('L')
    else:  # Auto: straightforward black/white threshold conversion.
        pass

    pix = gray.load()
    apix = alpha.load()
    result = []
    for cy in range(rows):
        line = []
        for cx in range(cols):
            bits = 0
            for dx, dy, bit in DOTS:
                x, y = cx * 2 + dx, cy * 4 + dy
                if transparent and apix[x, y] < 32:
                    continue
                value = pix[x, y]
                if mode == 'Convert to Line Art':
                    on = value < cutoff
                elif mode == 'Dither (shading)':
                    on = value < 128
                else:
                    on = value < int(threshold)
                if on:
                    bits |= bit
            line.append(chr(0x2800 + bits))
        result.append(''.join(line).rstrip() if transparent else ''.join(line))
    return '\n'.join(result), rows


class ImageTextApp:
    def __init__(self, root):
        self.root = root
        root.title('ImageText — Unicode Dot Art')
        root.geometry('1180x790'); root.minsize(900, 620); root.configure(bg=BG)
        self.image = None; self.image_path = None; self.art = ''; self._after_id = None
        self.mode = tk.StringVar(value='Auto')
        self.width = tk.IntVar(value=180)
        self.threshold = tk.IntVar(value=128)
        self.sensitivity = tk.DoubleVar(value=0.45)
        self.thickness = tk.IntVar(value=1)
        self.transparent = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value='Open an image to begin.')
        self._style(); self._ui()
        root.bind('<Control-o>', lambda e: self.open_image())
        root.bind('<Control-s>', lambda e: self.save_art())
        root.bind('<Control-Shift-c>', lambda e: self.copy_art())

    def _style(self):
        s = ttk.Style(); s.theme_use('clam')
        s.configure('TCombobox', fieldbackground=PANEL2, background=PANEL2, foreground=FG, arrowcolor=FG)
        s.map('TCombobox', fieldbackground=[('readonly', PANEL2)], foreground=[('readonly', FG)])
        s.configure('Horizontal.TScale', background=PANEL, troughcolor=PANEL2)
        s.configure('TCheckbutton', background=PANEL, foreground=FG)
        s.map('TCheckbutton', background=[('active', PANEL)], foreground=[('active', FG)])

    def _ui(self):
        header = tk.Frame(self.root, bg=BG); header.pack(fill='x', padx=24, pady=(18,14))
        titlebox = tk.Frame(header, bg=BG); titlebox.pack(side='left', fill='x', expand=True)
        tk.Label(titlebox, text='ImageText', bg=BG, fg=FG, font=('Segoe UI', 23, 'bold')).pack(anchor='w')
        tk.Label(titlebox, text='Convert pictures into pure black-and-white Unicode Braille art', bg=BG, fg=MUTED, font=('Segoe UI', 10)).pack(anchor='w', pady=(2,0))
        self._button(header, '＋  Open Image', self.open_image, ACCENT).pack(side='right')

        main = tk.Frame(self.root, bg=BG); main.pack(fill='both', expand=True, padx=24, pady=(0,12))
        main.grid_columnconfigure(0, minsize=285, weight=0); main.grid_columnconfigure(1, weight=1); main.grid_rowconfigure(0, weight=1)
        side = tk.Frame(main, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        side.grid(row=0, column=0, sticky='nsew', padx=(0,15)); side.grid_columnconfigure(0, weight=1)
        tk.Label(side, text='SETTINGS', bg=PANEL, fg=MUTED, font=('Segoe UI',9,'bold')).grid(row=0,column=0,sticky='w',padx=16,pady=(16,12))
        self.file_label = tk.Label(side, text='No image selected', bg=PANEL, fg=FG, font=('Segoe UI',10,'bold'), wraplength=245, anchor='w', justify='left')
        self.file_label.grid(row=1,column=0,sticky='ew',padx=16,pady=(0,12))
        self._label(side, 'MODE', 2)
        self.mode_box = ttk.Combobox(side, textvariable=self.mode, values=['Auto','Convert to Line Art','Dither (shading)'], state='readonly')
        self.mode_box.grid(row=3,column=0,sticky='ew',padx=16,pady=(0,4)); self.mode_box.bind('<<ComboboxSelected>>', self._schedule_convert)
        tk.Label(side, text='Choose the preprocessing that best suits your image.', bg=PANEL, fg=MUTED, wraplength=245, justify='left', font=('Segoe UI',8)).grid(row=4,column=0,sticky='w',padx=16,pady=(2,8))
        self._label(side, 'RESOLUTION', 5)
        self._slider(side, 6, self.width, 40, 360, 10, 'width', 'Smaller', 'More detailed')
        self._label(side, 'THRESHOLD / DARKNESS', 7)
        self._slider(side, 8, self.threshold, 20, 235, 1, 'threshold', 'Darker', 'Lighter')
        self._label(side, 'LINE SENSITIVITY', 9)
        self._slider(side, 10, self.sensitivity, 0.0, 1.0, 0.05, 'sensitivity', 'Fewer lines', 'More lines')
        self._label(side, 'LINE THICKNESS', 11)
        self._slider(side, 12, self.thickness, 0, 4, 1, 'thickness', 'Thinner', 'Thicker')
        ttk.Checkbutton(side, text='Keep transparent pixels blank', variable=self.transparent, command=self._schedule_convert).grid(row=13,column=0,sticky='w',padx=16,pady=(12,8))
        tk.Label(side, text='Line controls work in Line Art mode. Dither creates stippled shading.', bg=PANEL, fg=MUTED, wraplength=245, justify='left', font=('Segoe UI',8)).grid(row=14,column=0,sticky='w',padx=16,pady=(0,12))
        sep = tk.Frame(side,bg=BORDER,height=1); sep.grid(row=15,column=0,sticky='ew',padx=16,pady=3)
        actions = tk.Frame(side,bg=PANEL); actions.grid(row=16,column=0,sticky='ew',padx=16,pady=12); actions.grid_columnconfigure((0,1),weight=1)
        self._button(actions,'Reset Settings',self.reset,'#334155').grid(row=0,column=0,columnspan=2,sticky='ew',pady=3)
        self._button(actions,'Copy Art',self.copy_art,ACCENT).grid(row=1,column=0,sticky='ew',padx=(0,4),pady=3)
        self._button(actions,'Save TXT',self.save_art,'#087F5B').grid(row=1,column=1,sticky='ew',padx=(4,0),pady=3)

        right = tk.Frame(main,bg=BG); right.grid(row=0,column=1,sticky='nsew'); right.grid_columnconfigure(0,weight=1); right.grid_rowconfigure(1,weight=1)
        top = tk.Frame(right,bg=BG); top.grid(row=0,column=0,sticky='ew',pady=(0,8))
        tk.Label(top,text='DOT ART PREVIEW',bg=BG,fg=FG,font=('Segoe UI',12,'bold')).pack(side='left')
        self.count = tk.Label(top,text='0 characters',bg=BG,fg=MUTED,font=('Segoe UI',9)); self.count.pack(side='right')
        art_panel = tk.Frame(right,bg=PANEL,highlightbackground=BORDER,highlightthickness=1); art_panel.grid(row=1,column=0,sticky='nsew'); art_panel.grid_rowconfigure(0,weight=1); art_panel.grid_columnconfigure(0,weight=1)
        self.preview = tk.Text(art_panel,bg='#080A0F',fg='#F3F4F6',insertbackground=FG,selectbackground='#454078',font=('Consolas',9),wrap='none',relief='flat',padx=14,pady=14,undo=False)
        sy=ttk.Scrollbar(art_panel,orient='vertical',command=self.preview.yview); sx=ttk.Scrollbar(art_panel,orient='horizontal',command=self.preview.xview)
        self.preview.configure(yscrollcommand=sy.set,xscrollcommand=sx.set)
        self.preview.grid(row=0,column=0,sticky='nsew'); sy.grid(row=0,column=1,sticky='ns'); sx.grid(row=1,column=0,sticky='ew')
        self.preview.insert('1.0','Open an image to generate Braille dot art.'); self.preview.configure(state='disabled')
        footer=tk.Frame(self.root,bg=BG); footer.pack(fill='x',padx=24,pady=(0,13))
        tk.Label(footer,textvariable=self.status,bg=BG,fg=MUTED,font=('Segoe UI',9),anchor='w').pack(side='left',fill='x',expand=True)
        tk.Label(footer,text='Offline processing  •  Ctrl+O open  •  Ctrl+S save',bg=BG,fg='#65728A',font=('Segoe UI',9)).pack(side='right')

    def _label(self,parent,text,row):
        tk.Label(parent,text=text,bg=PANEL,fg=FG,font=('Segoe UI',9,'bold')).grid(row=row,column=0,sticky='w',padx=16,pady=(7,2))

    def _slider(self,parent,row,var,low,high,res,key,left,right):
        wrap=tk.Frame(parent,bg=PANEL); wrap.grid(row=row,column=0,sticky='ew',padx=16); wrap.grid_columnconfigure(0,weight=1)
        scale=tk.Scale(wrap,from_=low,to=high,resolution=res,orient='horizontal',variable=var,command=lambda _v:self._schedule_convert(),bg=PANEL,fg=FG,troughcolor=PANEL2,activebackground=ACCENT,highlightthickness=0,bd=0,showvalue=True,length=230)
        scale.grid(row=0,column=0,sticky='ew')
        tk.Label(wrap,text=left,bg=PANEL,fg=MUTED,font=('Segoe UI',8)).grid(row=1,column=0,sticky='w')
        tk.Label(wrap,text=right,bg=PANEL,fg=MUTED,font=('Segoe UI',8)).grid(row=1,column=0,sticky='e')

    def _button(self,parent,text,command,color):
        return tk.Button(parent,text=text,command=command,bg=color,fg='white',activebackground=color,activeforeground='white',relief='flat',bd=0,padx=13,pady=9,cursor='hand2',font=('Segoe UI',9,'bold'))

    def _schedule_convert(self,*_):
        if self._after_id: self.root.after_cancel(self._after_id)
        if self.image is not None: self._after_id=self.root.after(140,self.convert)

    def open_image(self):
        path=filedialog.askopenfilename(title='Choose an image',filetypes=[('Image files','*.png *.jpg *.jpeg *.webp *.bmp *.gif *.tif *.tiff'),('All files','*.*')])
        if not path:return
        try:
            im=Image.open(path); im.load(); self.image=im.convert('RGBA'); self.image_path=Path(path)
            self.file_label.configure(text=self.image_path.name); self.status.set(f'Loaded {im.width} × {im.height} image'); self.convert()
        except Exception as e: messagebox.showerror('Image Error',str(e))

    def convert(self,*_):
        self._after_id=None
        if self.image is None:return
        try:
            # UI resolution means Braille character columns, so clamp to practical range.
            self.art, rows=threshold_art(self.image,self.width.get(),self.mode.get(),self.threshold.get(),float(self.sensitivity.get()),self.thickness.get(),self.transparent.get())
            self.preview.configure(state='normal'); self.preview.delete('1.0','end'); self.preview.insert('1.0',self.art); self.preview.configure(state='disabled')
            self.count.configure(text=f'{len(self.art):,} characters')
            self.status.set(f'{self.mode.get()}  •  {self.width.get()} columns × {rows} lines')
        except Exception as e:messagebox.showerror('Conversion Error',str(e))

    def reset(self):
        self.mode.set('Auto'); self.width.set(180); self.threshold.set(128); self.sensitivity.set(0.45); self.thickness.set(1); self.transparent.set(True); self.convert()

    def copy_art(self):
        if not self.art:messagebox.showinfo('No Art','Open an image first.'); return
        try:self.root.clipboard_clear(); self.root.clipboard_append(self.art); self.root.update(); self.status.set('Unicode Braille art copied to clipboard.')
        except Exception as e:messagebox.showerror('Clipboard Error',str(e))

    def save_art(self):
        if not self.art:messagebox.showinfo('No Art','Open an image first.'); return
        default=(self.image_path.stem if self.image_path else 'image')+'_dot_art.txt'
        path=filedialog.asksaveasfilename(title='Save dot art',defaultextension='.txt',initialfile=default,filetypes=[('Text files','*.txt')])
        if not path:return
        try:Path(path).write_text(self.art,encoding='utf-8'); self.status.set(f'Saved {Path(path).name}')
        except Exception as e:messagebox.showerror('Save Error',str(e))

if __name__=='__main__':
    root=tk.Tk(); app=ImageTextApp(root); root.mainloop()
