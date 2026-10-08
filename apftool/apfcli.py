import sys
import os
import io
import apftool
from PIL import Image

exts = Image.registered_extensions()
supported_extensions = {ex for ex, f in exts.items() if f in Image.OPEN}

def main():
    print(f"apftool cli [v{apftool.version}] (c) 2026 Maristocratic Communications")

    if len(sys.argv) < 3:
        print("""Usage: apfcli <input_file> <output file>
arguents:

decoding:
--format=IMAGE-FORMAT

encoding:
--lineskip=INT - (APF/APF2) how many lines are skipped in progressive scanning. (default is 1)
--findbestlineskip - (APF/APF2) finds the lineskip value with the smallest file size. (APF2) search is limited to supplied lineskip argument (default is 10)

--desc=STR - (APF2) file description [Alias: -D=STR]
--legacy - (APF2) use bi-level runs
--transparent - (APF2) alias for --transmode=1
--transmode=INT - (APF2) sets transparency mode. 0 is off, 1 is index 0 is 00000000, 2 is 8-bit alpha in palette [Alias: -T=INT]
--palette=INT - (APF2) sets max colors. 2 will use legacy + bg.fg, >95 will use dual-indexed mode. 9025 is max.
--dither - (APF2) enables dithering (off by default outside of legacy) [Alias: -D]
--topdown - (APF2) reverses scan order
--uncompressed - (APF2) disables RLE (not applicable for legacy mode)
--combine - (APF2) apply cross-frame compression. Implicitly sets transmode to 1, except for mode 3 where it uses FE00FE as transparency. Unsupported on legacy. [Alias: -C]
--avoidrunbreaks - (APF2) avoid breaking runs on combine mode. May improve or harm efficiency (usually harm, as it is not tuned).
--run-quality=INT - (APF2) (0 to 100) allows for lossy RLE compression
--motion-quality=INT - (APF2) (0 to 100) allows for lossy motion compression (for --combine)
--quality=INT - (APF2) (0 to 100) sets both --run-quality and --motion-quality [Alias: -Q=INT]
--pillow - (APF2) use pillow's quantizer [Alias: -P]
--bayer - (APF2) use faster bayer/ordered dithering for perceptual mode instead of the slower, but prettier floyd-steinberg
--mode=INT - (APF2) color mode (specified in A2K) for APF2. [Alias: -M=INT]
    0 - 2 colors
    1 - 95 colors
    2 - 9025 colors
    3 - near-truecolor
    4 - near-truecolor with alpha
    5 - truecolor
    6 - truecolor with alpha
    7 - Mode 1-based Grayscale
    8 - Mode 2-based Grayscale

--width - (OTB/APF2) sets width (default is 255 for OTB, no scaling for APF2) [Alias: -W=INT]
--height - (OTB/APF2) sets height (default is 255 for OTB, no scaling for APF2) [Alias: -H=INT]

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
    lineskip = None
    dither = False
    description = ""
    if opext in apftool.extensions_apf2:
        wid = None
        hei = None
    else:
        wid = 255
        hei = 255
    transcolor = None
    flip = False
    compress = True
    mode = None
    combine = False
    avoid_run_breaks = False
    maxmotionerror = 0
    maxrunerror = 0
    useadvancedquant = True
    dither_mode = "fs"
    if args:
        if "--findbestlineskip" in args:
            fbls = True
        if "--legacy" in args:
            legacy = True
        if "--transparent" in args:
            trans = 1
        if "--dither" in args or "-D" in args:
            dither = True
        if "--topdown" in args:
            flip = True
        if "--uncompressed" in args:
            compress = False
        if "--combine" in args or "-C" in args:
            combine = True
        if "--magenta" in args:
            magenta = True
        if "--avoidrunbreaks" in args:
            avoid_run_breaks = True
        if "--pillow" in args or "-P" in args:
            useadvancedquant = False
        if "--bayer" in args:
            dither_mode = "ordered"
        for arg in args:
            if arg.startswith("--desc=") or arg.startswith("-D="):
                description = arg.replace("--desc=", "").replace("-D=", "")
            if arg.startswith("--format="):
                forma = arg.replace("--format=", "")
            if arg.startswith("--transmode=") or arg.startswith("-T="):
                trans = int(arg.replace("--transmode=", "").replace("-T=", ""))
            if arg.startswith("--palette="):
                maxpalette = int(arg.replace("--palette=", ""))
            if arg.startswith("--lineskip="):
                lineskip = int(arg.replace("--lineskip=", ""))

            if arg.startswith("--width=") or arg.startswith("-W="):
                wid = int(arg.replace("--width=", "").replace("-W=", ""))
            if arg.startswith("--height=") or arg.startswith("-H="):
                hei = int(arg.replace("--height=", "").replace("-H=", ""))

            if arg.startswith("--mode="):
                mode = int(arg.replace("--mode=", ""))
            if arg.startswith("-M="):
                mode = int(arg.replace("-M=", ""))

            if arg.startswith("--quality=") or arg.startswith("-Q="):
                qual = int(arg.replace("--quality=", "").replace("-Q=", ""))/2
                maxmotionerror = 50-qual
                maxrunerror = maxmotionerror

            if arg.startswith("--run-quality="):
                qual = int(arg.replace("--run-quality=", ""))/2
                maxrunerror = 50-qual

            if arg.startswith("--motion-quality="):
                qual = int(arg.replace("--motion-quality=", ""))/2
                maxmotionerror = 50-qual

            if arg.startswith("--transcolor="):
                transcolor_hex = arg.replace("--transcolor=", "").replace("#", "")
                tcr = int(transcolor_hex[0:2], 16)
                tcg = int(transcolor_hex[2:4], 16)
                tcb = int(transcolor_hex[4:6], 16)
                transcolor = (tcr, tcg, tcb)

        if mode is None:
            if maxpalette > 9025 and 857375 >= maxpalette:
                maxpalette = 95
                mode = 4 if trans == 2 else 3
            elif maxpalette > 857375:
                maxpalette = 95
                mode = 6 if trans == 2 else 5

    assert maxrunerror >= 0, f"Quality cannot be above 100 (got {maxrunerror})"
    assert maxmotionerror >= 0, f"Quality cannot be above 100 (got {maxrunerror})"

    res = f"Converting {input_path} to {output_path}..."
    if opext in apftool.extensions_apf2:
        md = mode
        if not md:
            if legacy:
                md = 0
            elif maxpalette > 95:
                md = 2
            else:
                md = 1
        res+= f" [Max Run Error: {maxrunerror}, Max Motion Error: {maxmotionerror}, Mode {md}]"
    print(res)

    # PNG to APF/APF2
    if opext in apftool.extensions_all:
        if ext in supported_extensions:
            img_bytes = Image.open(input_path)
        else:
            with open(input_path, "rb") as f:
                img_bytes = apftool.decode(f.read(), forma)

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
            encoded = apftool.apf2.encode(img_bytes, lineskip=lineskip, findbestlineskip=fbls, legacy=legacy, trans=trans, pal=maxpalette, desc=description, prepalette= None, dodithering=dither, returnbytes=True, compress=compress, topside_first=flip, mode=mode, combine=combine, avoid_run_breaks=avoid_run_breaks, width=wid, height=hei, maxrunerror = maxrunerror, maxmotionerror = maxmotionerror, verbose = True, useadvancedquant=useadvancedquant, dither_mode=dither_mode)

        else:
            raise ValueError("Unsupported Image Format!")
        with open(output_path, "wb") as f:
            f.write(encoded)
        print(f"Encoded {input_path} -> {output_path}")

    # APF/APF2 to PNG
    elif opext in supported_extensions:
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
