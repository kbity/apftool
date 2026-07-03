import sys
import os
import io
import apftool
from PIL import Image

exts = Image.registered_extensions()
supported_extensions = {ex for ex, f in exts.items() if f in Image.OPEN}

def main():
    if len(sys.argv) < 3:
        print("""Usage: apfcli <input_file> <output file>
arguents:

decoding:
--format=IMAGE-FORMAT

encoding:
--lineskip=INT - (APF/APF2) how many lines are skipped in progressive scanning.
--findbestlineskip - (APF/APF2) finds the lineskip value with the smallest file size. (APF2) search is limited to supplied lineskip argument (default is 1)
--legacy - (APF2) use bi-level runs
--transparent - (APF2) alias for transmode=1
--transmode=INT - (APF2) sets transparency mode. 0 is off, 1 is index 0 is 00000000, 2 is 8-bit alpha in palette
--palette=INT - (APF2) sets max colors. >95 will use dual-indexed mode. 9025 is max.
--dither - (APF2) enables dithering (off by default outside of legacy)

Supported decode formats: APF, APF2, WBMP, OTB, BRUH
Supported encode formats: APF, APF2

TODO: wbmp, bruh, and otb encoding
""")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    args = None
    if len(sys.argv) > 3:
        args = sys.argv[3:]
    base, ext = os.path.splitext(input_path)
    _, opext = os.path.splitext(output_path)
    ext = ext.lower()
    fbls = False
    legacy = False
    trans = 0
    forma = 'PNG'
    maxpalette = 95
    lineskip = 1
    dither = False
    description = ""
    if args:
        if "--findbestlineskip" in args:
            fbls = True
        if "--legacy" in args:
            legacy = True
        if "--transparent" in args:
            trans = 1
        if "--dither" in args:
            dither = True
        for arg in args:
            if arg.startswith("--format="):
                forma = arg.replace("--format=", "")
            if arg.startswith("--transmode="):
                trans = int(arg.replace("--transmode=", ""))
            if arg.startswith("--palette="):
                maxpalette = int(arg.replace("--palette=", ""))
            if arg.startswith("--lineskip="):
                lineskip = int(arg.replace("--lineskip=", ""))

    # PNG to APF/APF2
    if ext in supported_extensions:
        with open(input_path, "rb") as f:
            img_bytes = f.read()
        if opext in (".apf", ".aif"):
            encoded = apftool.encodeapf(img_bytes, lineskip=lineskip, findbestlineskip=fbls)
        else:
            encoded = apftool.encodeapf2(img_bytes, lineskip=lineskip, findbestlineskip=fbls, legacy=legacy, trans=trans, pal=maxpalette, desc=description, prepalette= None, dodithering=dither)
        with open(output_path, "w") as f:
            f.write(encoded)
        print(f"Encoded {input_path} -> {output_path}")

    # APF/APF2 to PNG
    elif ext in apftool.extensions_all:
        with open(input_path, "rb") as f:
            apf_content = f.read()
        decoded_bytes = apftool.decodeany(apf_content, forma)
        with open(output_path, "wb") as f:
            f.write(decoded_bytes)
        print(f"Decoded {input_path} -> {output_path}")

    else:
        print("Unsupported file type. Please use an image format supported by the encoder/decoder.")
        sys.exit(1)

if __name__ == "__main__":
    main()
