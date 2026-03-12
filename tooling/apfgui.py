import tkinter as tk
from tkinter import filedialog, messagebox
import os
import apftool
from PIL import Image

exts = Image.registered_extensions()
supported_extensions = {ex for ex, f in exts.items() if f in Image.OPEN}


def convert():
    input_path = input_entry.get()
    output_path = output_entry.get()

    if not input_path or not output_path:
        messagebox.showerror("Error", "Please select input and output files.")
        return

    fbls = findbest_var.get()
    legacy = legacy_var.get()
    trans = trans_var.get()

    lineskip = int(lineskip_entry.get())
    palette = int(palette_entry.get())
    forma = format_var.get()

    base, ext = os.path.splitext(input_path)
    _, opext = os.path.splitext(output_path)
    ext = ext.lower()

    try:
        if ext in supported_extensions:
            with open(input_path, "rb") as f:
                img_bytes = f.read()

            if opext in (".apf", ".aif"):
                encoded = apftool.encodeapf(
                    img_bytes,
                    lineskip=lineskip,
                    findbestlineskip=fbls
                )
            else:
                encoded = apftool.encodeaf2(
                    img_bytes,
                    lineskip=lineskip,
                    findbestlineskip=fbls,
                    legacy=legacy,
                    trans=trans,
                    pal=palette
                )

            with open(output_path, "w") as f:
                f.write(encoded)

        elif ext in apftool.extensions:
            with open(input_path, "r") as f:
                apf_content = f.read()

            decoded_bytes = apftool.decodeaf2(apf_content, forma)

            with open(output_path, "wb") as f:
                f.write(decoded_bytes)

        else:
            messagebox.showerror("Error", "Unsupported file type.")
            return

        messagebox.showinfo("Success", "Conversion completed!")

    except Exception as e:
        messagebox.showerror("Error", str(e))


def browse_input():
    file = filedialog.askopenfilename()
    input_entry.delete(0, tk.END)
    input_entry.insert(0, file)


def browse_output():
    file = filedialog.asksaveasfilename()
    output_entry.delete(0, tk.END)
    output_entry.insert(0, file)


root = tk.Tk()
root.title("APF/AF2 Converter")

# Input
tk.Label(root, text="Input File").grid(row=0, column=0)
input_entry = tk.Entry(root, width=40)
input_entry.grid(row=0, column=1)
tk.Button(root, text="Browse", command=browse_input).grid(row=0, column=2)

# Output
tk.Label(root, text="Output File").grid(row=1, column=0)
output_entry = tk.Entry(root, width=40)
output_entry.grid(row=1, column=1)
tk.Button(root, text="Browse", command=browse_output).grid(row=1, column=2)

# Options
findbest_var = tk.BooleanVar()
legacy_var = tk.BooleanVar()
trans_var = tk.BooleanVar()

tk.Checkbutton(root, text="Find Best Lineskip", variable=findbest_var).grid(row=2, column=0, sticky="w")
tk.Checkbutton(root, text="Legacy Mode", variable=legacy_var).grid(row=3, column=0, sticky="w")
tk.Checkbutton(root, text="Transparency", variable=trans_var).grid(row=4, column=0, sticky="w")

# Lineskip
tk.Label(root, text="Lineskip").grid(row=2, column=1)
lineskip_entry = tk.Entry(root)
lineskip_entry.insert(0, "1")
lineskip_entry.grid(row=2, column=2)

# Palette
tk.Label(root, text="Palette Size").grid(row=3, column=1)
palette_entry = tk.Entry(root)
palette_entry.insert(0, "95")
palette_entry.grid(row=3, column=2)

# Format
tk.Label(root, text="Decode Format").grid(row=4, column=1)
format_var = tk.StringVar(value="PNG")
format_menu = tk.OptionMenu(root, format_var, "PNG", "GIF", "BMP", "WEBP")
format_menu.grid(row=4, column=2)

# Convert button
tk.Button(root, text="Convert", command=convert, height=2).grid(row=5, column=0, columnspan=3, pady=10)

root.mainloop()
