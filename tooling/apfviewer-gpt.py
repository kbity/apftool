import PIL, sys, os, io
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from apftool import decodeaf2, extensions

tupleware = []
cf = 0
limit = 0

for ex in extensions:
    tupleware.append(('Aperture Image Format', ex))
tupleware = tuple(tupleware)

if len(sys.argv) < 2:
    filename = filedialog.askopenfilename(filetypes=tupleware)
else:
    filename = sys.argv[1]

if not isinstance(filename, str):
    quit()

base, ext = os.path.splitext(filename)

if ext not in extensions:
    messagebox.showerror("Error", "Unsupported file, please use an APF or AF2 Image.")
    quit()

with open(filename, "r") as f:
    data = f.read()

root = tk.Tk()
root.title("apfviewer")

imgdat = decodeaf2(data, 'BRUH', True)

if isinstance(imgdat, list):
    animated = True
else:
    animated = False
    imgdat = [imgdat]

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
    label.config(image=tk_image)
    label.image = tk_image

    cf = (cf + 1) % limit

    root.after(100, animate)


# ---------- resize handling ----------
def resize(event):
    global current_size
    current_size = (event.width, event.height)


root.bind("<Configure>", resize)

# ---------- start viewer ----------
animate()
root.mainloop()
