import PIL, sys, os, io
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from apftool import decodeany, extensions, extensions_wbmp, extensions_otab, extensions, extensions_all

def close(event):
    root.destroy()

tupleware = []
cf = 0
limit = 0
frametime = 50

for ex in extensions:
    tupleware.append(('Aperture Image Format', ex))
for ex in extensions_wbmp:
    tupleware.append(('Wireless Bitmap', ex))
for ex in extensions_otab:
    tupleware.append(('Over The Air Bitmap', ex))
tupleware = tuple(tupleware)

if len(sys.argv) < 2:
    filename = filedialog.askopenfilename(filetypes=tupleware)
else:
    filename = sys.argv[1]

if not isinstance(filename, str):
    quit()

base, ext = os.path.splitext(filename)

wbmp = False
if ext not in extensions:
    if ext in extensions_wbmp or ext in extensions_otab:
        wbmp = True
    elif ext in extensions_all:
        pass
    else:
        messagebox.showerror("Error", "Unsupported file, please use an APF, AF2, WBMP, OTB, or BRUH Image.")
        quit()

root = tk.Tk()
root.title(f"{filename} - apfviewer")

root.bind("<Escape>", close)

with open(filename, "rb") as f:
    data = f.read()
imgdat = decodeany(data, 'BRUH', True)

if isinstance(imgdat, list):
    animated = True
    frametime = data.decode('ascii')
    frametime = frametime.splitlines()[1]
    frametime = frametime.split(",")
    if len(frametime) == 5:
        frametime = frametime[4]
        frametime = int(frametime)
    else:
        frametime = 100
else:
    animated = False
    imgdat = [imgdat]
    if wbmp:
        imgdat = [img.point(lambda p: 0 if p == 0 else 255) for img in imgdat]

limit = len(imgdat)

orig_w, orig_h = imgdat[0].size
root.geometry(f"{orig_w}x{orig_h}")

label = tk.Label(root)
label.pack(fill="both", expand=True)

current_size = (orig_w, orig_h)


# ---------- image scaling ----------
def scale_image(img, size):
    w, h = img.size
    tw, th = size

    scale = min(tw / w, th / h)

    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))

    return img.resize((new_w, new_h), Image.NEAREST)


# ---------- animation ----------
def animate():
    global cf

    frame = scale_image(imgdat[cf], current_size)

    tk_image = ImageTk.PhotoImage(frame)
    label.config(image=tk_image, bg='black')
    label.image = tk_image

    cf = (cf + 1) % limit

    root.after(frametime, animate)


# ---------- resize handling ----------
def resize(event):
    global current_size
    current_size = (event.width, event.height)


root.bind("<Configure>", resize)

# ---------- start viewer ----------
animate()
root.mainloop()
