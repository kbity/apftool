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
--width - (OTB) sets width (default is 255)
--height - (OTB) sets height (default is 255)
--transcolor - (MQIF) sets color to be made transparent (default is None)

Supported decode formats: APF, APF2, WBMP, OTB, BRUH, MQIF
Supported encode formats: APF, APF2, WBMP, OTB, BRUH

TODO: MQIF encoding
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
    wid = 255
    hei = 255
    transcolor = None
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
            if arg.startswith("--width="):
                wid = int(arg.replace("--width=", ""))
            if arg.startswith("--height="):
                hei = int(arg.replace("--height=", ""))
            if arg.startswith("--transcolor="):
                transcolor_hex = arg.replace("--transcolor=", "").replace("#", "")
                tcr = int(transcolor_hex[0:2], 16)
                tcg = int(transcolor_hex[2:4], 16)
                tcb = int(transcolor_hex[4:6], 16)
                transcolor = (tcr, tcg, tcb)

    # PNG to APF/APF2
    if ext in supported_extensions:
        img_bytes = Image.open(input_path)
        if opext in apftool.extensions_apf:
            encoded = apftool.apf.encode(img_bytes, lineskip=lineskip, findbestlineskip=fbls)
        elif opext in apftool.extensions_wbmp:
            encoded = apftool.wbmp.encode(img_bytes)
        elif opext in apftool.extensions_otb:
            encoded = apftool.otb.encode(img_bytes, width=wid, height=hei)
        elif opext in apftool.extensions_bruh:
            encoded = apftool.bruh.encode(img_bytes)
        elif opext in apftool.extensions_mqif:
            encoded = apftool.mqif.encode(img_bytes, transcolor)
        elif opext in apftool.extensions_apf2:
            encoded = apftool.apf2.encode(img_bytes, lineskip=lineskip, findbestlineskip=fbls, legacy=legacy, trans=trans, pal=maxpalette, desc=description, prepalette= None, dodithering=dither, returnbytes=True)
        else:
            raise ValueError("Unsupported Image Format!")
        with open(output_path, "wb") as f:
            f.write(encoded)
        print(f"Encoded {input_path} -> {output_path}")

    # APF/APF2 to PNG
    elif ext in apftool.extensions_all:
        with open(input_path, "rb") as f:
            apf_content = f.read()
        decoded_bytes = apftool.decode(apf_content, forma)
        with open(output_path, "wb") as f:
            f.write(decoded_bytes)
        print(f"Decoded {input_path} -> {output_path}")

    else:
        print("Unsupported file type. Please use an image format supported by the encoder/decoder.")
        sys.exit(1)

if __name__ == "__main__":
    main()
