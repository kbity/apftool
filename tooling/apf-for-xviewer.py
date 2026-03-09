import sys, io, os, apftool, subprocess

path = "/tmp/apf_preview.png"

def main():
    if len(sys.argv) < 2:
        print("Usage: python apf-for-xviewer.py <input_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    base, ext = os.path.splitext(input_path)
    ext = ext.lower()

    # APF → PNG
    if ext == ".apf":
        with open(input_path, "r") as f:
            apf_content = f.read()
        decoded_bytes = apftool.decodeapf(apf_content)
        output_path = base + ".png"
        with open(path, "wb") as f:
            f.write(decoded_bytes)
        subprocess.Popen(["xviewer", path])

    else:
        print("Unsupported file type. Use APF.")
        sys.exit(1)

if __name__ == "__main__":
    main()
