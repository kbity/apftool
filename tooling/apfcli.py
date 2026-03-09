import sys
import os
import io
import apftool

def main():
    if len(sys.argv) < 2:
        print("Usage: python apfcli.py <input_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base, ext = os.path.splitext(input_path)
    ext = ext.lower()

    # PNG → APF
    if ext in [".png", ".jpg", ".jpeg", ".bmp"]:
        with open(input_path, "rb") as f:
            img_bytes = f.read()
        encoded = apftool.encodeapf(img_bytes, lineskip=3, findbestlineskip=True)
        output_path = base + ".apf"
        with open(output_path, "w") as f:
            f.write(encoded)
        print(f"Encoded {input_path} → {output_path}")

    # APF → PNG
    elif ext == ".apf":
        with open(input_path, "r") as f:
            apf_content = f.read()
        decoded_bytes = apftool.decodeapf(apf_content)
        output_path = base + ".png"
        with open(output_path, "wb") as f:
            f.write(decoded_bytes)
        print(f"Decoded {input_path} → {output_path}")

    else:
        print("Unsupported file type. Use PNG or APF.")
        sys.exit(1)

if __name__ == "__main__":
    main()