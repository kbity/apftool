import PIL, sys, os
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from apftool import decodeaf2, extensions

tupleware = []
cf = 0
limit = 0

for ex in extensions:
    tupleware.append(('Aperture Image Format', ex))
tuple(tupleware)

if len(sys.argv) < 2:
    filename = filedialog.askopenfilename(filetypes=tupleware)
else:
    filename = sys.argv[1]

if not isinstance(filename, str):
    quit()

base, ext = os.path.splitext(filename)

if not ext in extensions:
    messagebox.showerror("Error", "Unsupported file, please use an APF or AF2 Image.")
    quit()

with open(filename, "r") as f:
    data = f.read()
root = tk.Tk()
root.title('apfviewer')

imgdat = decodeaf2(data, 'BRUH', True)
if isinstance(imgdat, list):
    animated = True
    #imgdat = imgdat[0]
else:
    animated = False

def animate(label):
    global cf
    global limit

    tk_image = ImageTk.PhotoImage(imgdat[cf])
    label.config(image=tk_image)
    label.image = tk_image

    cf += 1
    if cf >= limit:
        cf = 0

    root.after(100, animate, label)


if animated:
    limit = len(imgdat)
    cf = 0

    label = tk.Label(root)
    label.pack()

    animate(label)
    root.mainloop()

else:
    tk_image = ImageTk.PhotoImage(imgdat)
    label = tk.Label(root, image=tk_image)
    label.pack()
    root.mainloop()
