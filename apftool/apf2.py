from PIL import Image, ImageSequence
from collections import Counter
import io, textwrap

qmf = "basic"

# try numpy and sklearn
try:
    import numpy as np
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.metrics import pairwise_distances_argmin
    qmf = "sk"
except Exception as e:
    print(f"Importing sklearn or numpy failed, high-color images and images with alpha may encode slowly or not at all, and dithering will be unavailable for them!\n{e}")

# width and height are 320x200 for standard apf files
apf2headertext = "APERTURE IMAGE FORMAT (c) 1993" # apf2 header
apf2headertext1994 = "APERTURE IMAGE FORMAT (c) 1994" # apf2 header (1994 extensions of d, and a)
apf2headertext2000 = "APERTURE IMAGE FORMAT (c) 2000" # a2k header (2000 extensions of c, and u, U, A, T, n, q)

# precompute lookup table for base256-to-base95
def quant_to_base95(g: int):
    X = 255/94
    return round(g/X)

mapping = []
for i in range(256):
    mapping.append(chr(quant_to_base95(i)+32))

# fast sklearn version
def quantize_most_frequent_sk(img: Image.Image, n_colors: int, palette: list = None, dither: bool = False):
    img = img.convert("RGBA")
    arr = np.array(img, dtype=np.uint8)
    flat = arr.reshape(-1, 4).astype(np.float32)

    if palette is not None:
        # ---- FIXED PALETTE MODE ----
        palette_arr = np.array(palette, dtype=np.uint8)
    else:
        # ---- KMEANS MODE ----
        kmeans = MiniBatchKMeans(
            n_clusters=n_colors,
            batch_size=10_000,
            n_init="auto",
            random_state=0
        )
        kmeans.fit(flat)
        palette_arr = kmeans.cluster_centers_.astype(np.uint8)

    if dither:
        # Floyd-Steinberg dithering — operate on a float copy to accumulate error
        h, w = arr.shape[:2]
        buf = arr.astype(np.float32)  # (H, W, 4)

        out_indices = np.empty((h, w), dtype=np.int32)

        for y in range(h):
            # Serpentine scan (alternating direction) reduces directional bias
            xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
            for x in xs:
                old = buf[y, x]
                idx = pairwise_distances_argmin(old[np.newaxis], palette_arr)[0]
                out_indices[y, x] = idx
                new = palette_arr[idx].astype(np.float32)
                err = old - new

                # Distribute error to 4 neighbours (Floyd-Steinberg weights)
                if y % 2 == 0:  # left-to-right
                    if x + 1 < w:
                        buf[y,     x + 1] += err * (7 / 16)
                    if y + 1 < h:
                        if x - 1 >= 0:
                            buf[y + 1, x - 1] += err * (3 / 16)
                        buf[y + 1, x    ] += err * (5 / 16)
                        if x + 1 < w:
                            buf[y + 1, x + 1] += err * (1 / 16)
                else:           # right-to-left
                    if x - 1 >= 0:
                        buf[y,     x - 1] += err * (7 / 16)
                    if y + 1 < h:
                        if x + 1 < w:
                            buf[y + 1, x + 1] += err * (3 / 16)
                        buf[y + 1, x    ] += err * (5 / 16)
                        if x - 1 >= 0:
                            buf[y + 1, x - 1] += err * (1 / 16)

        quantized = palette_arr[out_indices].reshape(arr.shape)
    else:
        labels = pairwise_distances_argmin(flat, palette_arr)
        quantized = palette_arr[labels].reshape(arr.shape)

    palette_out = [tuple(map(int, x)) for x in palette_arr]
    return Image.fromarray(quantized, "RGBA"), palette_out

# slow pure python version
def quantize_most_frequent_basic(img: Image.Image, n_colors: int, palette: list = None, dither: bool = False): # for use with A and P>256 images, dithering unsupported for basic mode
    img = img.convert("RGBA")  # ensures consistent format
    pixels = list(img.getdata())

    # do this if a palette is not provided
    if not palette:
        # Count colors
        counts = Counter(pixels)
        # Take top N colors
        palette = [color for color, _ in counts.most_common(n_colors)]

    # Precompute for speed
    def dist2(c1, c2):
        return (
            (c1[0] - c2[0]) ** 2 +
            (c1[1] - c2[1]) ** 2 +
            (c1[2] - c2[2]) ** 2 +
            (c1[3] - c2[3]) ** 2
        )

    # Map pixels to nearest palette color
    new_pixels = []
    for p in pixels:
        closest = min(palette, key=lambda c: dist2(p, c))
        new_pixels.append(closest)

    # Build output image
    out = Image.new("RGBA", img.size)
    out.putdata(new_pixels)

    return out, palette

if qmf == "sk":
    quantize_most_frequent = quantize_most_frequent_sk
#elif qmf == "numpy":   removed the numpy backend because it was having problems
#    quantize_most_frequent = quantize_most_frequent_numpy
else:
    quantize_most_frequent = quantize_most_frequent_basic

# splits apf2 data into the datapoints.
def split_datapoints(data: str, datlen: int):
    leng = len(data)

    trunc = False
    if not leng%datlen == 0:
        print("Error: Data must be divisible by the apf2 segment length! Attempting decode anyways...")
        trunc = True

    split_points = []

    for n in range(0, leng, datlen):
        split_points.append(data[n:(n+datlen)])

    if trunc:
        split_points.pop(-1)

    return split_points

def apf2_apfdecodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: list, trans: bool = False, topdown: bool = False):
    x = 0
    if topdown:
        y = 0
    else:
        y = h-1
    passoffset = 0
    state = False # swapping this will invert the image.

    for char in data:
        runlen = ord(char) - 32
        for i in range(runlen):
            if 0 <= y < len(apfbuffer) and 0 <= x < len(apfbuffer[0]):
                apfbuffer[y][x] = (state)
            x += 1

            if topdown:
                if x >= w:
                    y += lineskip
                    x = 0

                if y >= h:
                    passoffset +=1
                    y = passoffset
            else:
                if x >= w:
                    y -= lineskip
                    x = 0

                if y < 0:
                    passoffset +=1
                    y = (h-1)-passoffset

        state = not state

    colmode = "RGB"
    if trans:
        colmode+="A"
    img = Image.new(colmode, (w, h))
    pixels = img.load()

    for y in range(h):
        row = apfbuffer[y]

        for x in range(w):
            if row[x]:
                pixels[x, y] = pals[1]
            else:
                pixels[x, y] = pals[0]
    return img

def flexTypeToRGB(inpt: str, mode: int, trans: bool = False):
    # 3 - near-truecolor
    # 4 - near-truecolor with alpha
    # 5 - truecolor (can be paired with t to store 3 levels of alpha)
    # 6 - truecolor with alpha
    if mode == 3:
        r = mapping.index(inpt[0])
        g = mapping.index(inpt[1])
        b = mapping.index(inpt[2])
        r = r+int(r == 254)
        g = g+int(g == 254)
        b = b+int(b == 254)
        return r, g, b

    elif mode == 4:
        r = mapping.index(inpt[0])
        g = mapping.index(inpt[1])
        b = mapping.index(inpt[2])
        a = mapping.index(inpt[3])
        r = r+int(r == 254)
        g = g+int(g == 254)
        b = b+int(b == 254)
        a = a+int(a == 254)
        return r, g, b, a

    elif mode == 5:
        r = mapping.index(inpt[0])
        g = mapping.index(inpt[1])
        b = mapping.index(inpt[2])

        # compute corrections
        c = ord(inpt[3])-32
        rc = c%3
        gc = (c//3)%3
        bc = (c//9)%3
        ac = (c//27)%3

        if trans:
            return r+rc, g+gc, b+bc, (0, 128, 255)[ac]
        else:
            return r+rc, g+gc, b+bc

    elif mode == 6:
        r = mapping.index(inpt[0])
        g = mapping.index(inpt[1])
        b = mapping.index(inpt[2])
        a = mapping.index(inpt[3])

        # compute corrections
        c = ord(inpt[4])-32
        rc = c%3
        gc = (c//3)%3
        bc = (c//9)%3
        ac = (c//27)%3

        return r+rc, g+gc, b+bc, a+ac
    else:
        raise ValueError("Invalid/Unsupported Mode")

def apf2decodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: str, trans = 0, splitlen: int = 2, uncompressed: bool = False, mode: int = 1, topdown: bool = False):
    x = 0
    if topdown:
        y = 0
    else:
        y = h-1
    passoffset = 0

    # convert palette to dictionary tuples
    istrans2 = bool(trans == 2)

    flexMode = mode > 2 and mode < 7
    graymode = mode > 6

    if not flexMode and not graymode:
        pal = apf2palettedecode(pals, bool(mode-1), istrans2, False)
        if trans == 1:
            pal[" "*mode] = (0, 0, 0, 0)

    if graymode:
        if mode == 7:
            pal = graypal(False)
        else:
            pal = graypal(True)

    cdpts = split_datapoints(data, splitlen)

    for point in cdpts:
        if uncompressed:
            color = point
            runlen = 1
        else:
            color = point[:-1]
            runlen = ord(point[-1]) - 32

        for i in range(runlen):
            if 0 <= y < len(apfbuffer) and 0 <= x < len(apfbuffer[0]):
                if flexMode:
                    apfbuffer[y][x] = flexTypeToRGB(color, mode, bool(trans))
                else:
                    apfbuffer[y][x] = pal[color]

            x += 1
            if topdown:
                if x >= w:
                    y += lineskip
                    x = 0

                if y >= h:
                    passoffset +=1
                    y = passoffset
            else:
                if x >= w:
                    y -= lineskip
                    x = 0

                if y < 0:
                    passoffset +=1
                    y = (h-1)-passoffset

    colmode = "RGB"
    if trans:
        colmode+="A"
    img = Image.new(colmode, (w, h))
    pixels = img.load()

    for y in range(h):
        row = apfbuffer[y]

        for x in range(w):
            if not row[x]:
                pixels[x, y] = (255,0,255)
            else:
                pixels[x, y] = row[x]

    return img

def apf2palettedecode(pal: str, dim: bool = False, alpha: bool = False, dump: bool = True):
    tupledump = []
    statepal = {}
    tullength = 7
    il = 1
    if alpha:
        tullength += 2
    if dim:
        il = 2
        tullength += 1

    palsegments = [pal[i:i+tullength] for i in range(0, len(pal), tullength)]

    if alpha:
        for col in palsegments:
            ind = col[:il]
            hexcs = col[il:]
            hexcsegment = textwrap.wrap(hexcs, 2)
            if dump:
                tupledump.append((int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16),int(hexcsegment[3], 16)))
            else:
                statepal[ind] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16),int(hexcsegment[3], 16))
    else:
        for col in palsegments:
            ind = col[:il]
            hexcs = col[il:]
            hexcsegment = textwrap.wrap(hexcs, 2)
            if dump:
                tupledump.append((int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16), 255))
            else:
                statepal[ind] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

    if dump:
        return tupledump
    else:
        return statepal

def graypal(perfect: bool = False):
    pal = {}
    if perfect:
        for n in range(256):
            i0 = n%95
            i1 = n//95
            ind = chr(i1+32)+chr(i0+32)
            pal[ind] = (n, n, n)
    else:
        for n in set(mapping):
            if not n in pal:
                pal[n] = (mapping.index(n), mapping.index(n), mapping.index(n))
    return pal

def int_alpha_composit(l1: tuple, l2: tuple):
    # l1 is bottom, l2 is top
    a1 = l1[3]
    a2 = l2[3]

    r1 = l1[0]
    r2 = l2[0]
    r1 = r1*(255-a2) # sorta fixed point
    r2 = r2*a2

    g1 = l1[1]
    g2 = l2[1]
    g1 = g1*(255-a2) # sorta fixed point
    g2 = g2*a2

    b1 = l1[2]
    b2 = l2[2]
    b1 = b1*(255-a2) # sorta fixed point
    b2 = b2*a2

    ac = a1+(a2*(255-a1)//255)
    rc = (r1+r2) // 255
    gc = (g1+g2) // 255
    bc = (b1+b2) // 255

    return rc, gc, bc, ac

def blend_images(base, overlay):
    w, h = base.size
    b = base.load()
    o = overlay.load()
    for x in range(w):
        for y in range(h):
            b[x,y] = int_alpha_composit(b[x,y], o[x,y])
    return base

def diff_images(base, overlay, magenter = False):
    w, h = base.size
    b = base.load()
    o = overlay.load()
    blanks = {(0,0,0,0)}
    if magenter:
        blanks.add((255,0,255,255))
        blanks.add((255,0,255))

    for x in range(w):
        for y in range(h):
            if o[x,y] in blanks:
                o[x,y] = b[x,y]
    return overlay

def decode(apf2: str | bytes, format: str = 'PNG', returnImageObject: bool = False, provide_extra_data: bool = False, composite_layers: bool = True):
    if type(apf2) == bytes:
        apf2 = apf2.decode("ascii")

    apf_list = apf2.splitlines()
    apf_lines = []
    for line in apf_list:
        if line:
            apf_lines.append(line)

    if apf_lines[0].strip() == "APERTURE IMAGE FORMAT (c) 1985": # on the fly apf2 upgrade
        apf2 = f"APERTURE IMAGE FORMAT (c) 1993\n320x200,l,{apf_list[1]}\n.\n{apf_list[2]}"
        apf_lines = apf2.splitlines()

    if not apf_lines[0].strip() == apf2headertext and not apf_lines[0].strip() == apf2headertext1994 and not apf_lines[0].strip() == apf2headertext2000:
        raise Exception("Invalid/Unsupported Aperture Image Format File")

    metadata = apf_lines[1].strip().split(",")
    if len(metadata) > 4:
        delay = int(metadata[4])
    else:
        delay = 100
    res = metadata[0]
    res = res.split("x")
    w = int(res[0])
    h = int(res[1])
    arguments = metadata[1]
    lineskip = int(metadata[2])

    data = apf_lines[3:]

    # modes:
    # 0 - 2 colors
    # 1 - 95 colors
    # 2 - 9025 colors
    # 3 - near-truecolor
    # 4 - near-truecolor with alpha
    # 5 - truecolor
    # 6 - truecolor with alpha
    # 7 - Mode 1-based Grayscale
    # 8 - Mode 2-based Grayscale

    mode = 1 # standard mode
    tulplen = 2 # standard tuple length, IR
    animated = False # don't return an animation
    transparency_mode = 0 # no transparency

    composted = False # for apf2 animation, which does not use cross-frame compression unless the 2000 version's c flag is present
    uncompressed = False # RLE is on
    topdownscan = False # Bottom-top Scanning is default

    magenter = False # Edge Case for q images, treat FE00FE/~ ~ as 00000000 (pure black alpha)

    for arg in arguments:
        # color modes
        if arg == "l": # Legacy
            mode = 0
            tulplen = 1 # R
        elif arg == "i": # Index
            mode = 1
            tulplen = 2 # IR
        elif arg == "d": # Dual-index
            mode = 2
            tulplen = 3 # IIR
        elif arg == "q": # Quality mode
            mode = 3
            tulplen = 4 # RGBR
        elif arg == "n": # Near-truecolor + alpha
            mode = 4
            tulplen = 5 # RGBAR
            transparency_mode = 2 # implicit to the mode
        elif arg == "T": # Truecolor
            mode = 5
            tulplen = 5 # RGBCR
        elif arg == "A": # truecolor + Alpha
            mode = 6
            tulplen = 6 # RGBACR
            transparency_mode = 2 # implicit to the mode
        # Index-based Grayscale modes
        elif arg == "g": # 95-color Grayscale
            mode = 7
            tulplen = 2 # IR
        elif arg == "G": # 8-bit Grayscale
            mode = 8
            tulplen = 3 # IIR

        # data modes
        elif arg == "m": # Multistream
            animated = True
        elif arg == "c": # Combine
            composted = True
        elif arg == "u": # Upside down
            topdownscan = True
        elif arg == "U": # Uncompressed
            uncompressed = True

        # Transparency modes
        elif arg == "t": # Transparency
            transparency_mode = 1
        elif arg == "a": # Alpha transparency
            transparency_mode = 2
        elif arg == "M": # Magenta transparency
            magenter = True


    if uncompressed:
        tulplen -= 1 # removing R reduces RLE size
    if tulplen == 0:
        raise ValueError("Invalid Image! Legacy images cannot be uncompressed!")

    apfbuffer = []
    for i in range((h)):
        row = []
        for e in range((w)):
            row.append(None)
        apfbuffer.append(row)

    imgs = []

    uncompressed

    if mode == 0:
        pals = apf_lines[2].split(".")
        if pals[0] == "":
            if transparency_mode:
                pals[0] = (0,0,0,0)
            else:
                pals[0] = (0,0,0)
        else:
            hexcsegment = textwrap.wrap(pals[0], 2)
            if transparency_mode == 2:
                pals[0] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16),int(hexcsegment[3], 16))
            else:
                pals[0] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

        if pals[1] == "":
            pals[1] = (255,255,255)
        else:
            hexcsegment = textwrap.wrap(pals[1], 2)
            if transparency_mode == 2:
                pals[1] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16),int(hexcsegment[3], 16))
            else:
                pals[1] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

        for ds in data:
            imgs.append(apf2_apfdecodedata(ds, h, w, apfbuffer, lineskip, pals, transparency_mode, topdownscan))

    elif mode in (1, 2, 3, 4, 5, 6, 7, 8):
        pals = apf_lines[2]
        for ds in data:
            imgs.append(apf2decodedata(ds, h, w, apfbuffer, lineskip, pals, transparency_mode, tulplen, uncompressed, mode, topdownscan))
    else:
        raise NotImplementedError("Full A2K Decoding is not supported")

    multiple_streams = (len(imgs) > 1)

    if animated and composted:
        baseimg = imgs[0]
        imgs_new = [baseimg.copy()]
        for img in imgs[1:]:
            baseimg = diff_images(baseimg, img, magenter)
            imgs_new.append(baseimg.copy())
        imgs = imgs_new

    if multiple_streams and animated and not returnImageObject:
        multiple_streams = True
        imageData = io.BytesIO()

        if mode > -1: # covers mode 2+ which use more colors than GIF's 256 max colors
            imgs[0].save(imageData, format="WebP", save_all=True, append_images=imgs[1:], loop=0, duration=delay, disposal=2, lossless=True)
        else:
            imgs[0].save(imageData, format="GIF", save_all=True, append_images=imgs[1:], loop=0, duration=delay, disposal=2)

        imageData = imageData.getvalue()

    elif (not multiple_streams) and animated:
        animated = False # don't return an animation

    if multiple_streams and not animated and composite_layers:
        baseimg = imgs[0]
        for img in imgs[1:]:
            baseimg = blend_images(baseimg, img)
        imgs = [baseimg]

    if returnImageObject:
        if animated:
            if provide_extra_data:
                return imgs, delay # list object, be careful
            else:
                return imgs
        else:
            return imgs[0]

    else:
        if animated:
            return imageData
        else:
            imageData = io.BytesIO()
            imgs[0].save(imageData, format=format)
            imageData = imageData.getvalue()
            return imageData

def slice_frames(img: Image, animated, trans):
    frametiming = None

    colmod = "RGB"
    if trans:
        colmod+="A"
    frames = []

    if animated:
        for frame in ImageSequence.Iterator(img):
            if not frametiming:
                frametiming = frame.info.get("duration", img.info.get("duration", 0))
            frame = frame.convert(colmod)
            frames.append(frame)
        return frames, frametiming
    else:
        return img, None

def reduce_to_apf2_quality(img: Image, num_colors: int = 95, animated: bool = False, trans = 0, prepalette: list = None, dodithering: bool = False):
    trans = int(trans)
    if animated:
        # avoid expensive repeated hi-color quantize computing of every frame
        if trans == 2:
            trans = 1
        if num_colors > 256:
            num_colors = 256
            if trans:
                num_colors = 255
            print("Animation Detected, capping colors to 255/256")
        if dodithering:
            print("Animated APF2s do not get dithered, sorry.")

        ifuckinghatequantize = (255, 0, 255)

        frames = []
        frametiming = 0
        if trans:
            for frame in ImageSequence.Iterator(img):
                if not frametiming:
                    frametiming = frame.info.get("duration", img.info.get("duration", 0))

                frame = frame.convert("RGBA")
                background = Image.new("RGBA", frame.size, ifuckinghatequantize + (255,))
                composited = Image.alpha_composite(background, frame)
                frames.append(composited.convert("RGB"))
        else:
            for frame in ImageSequence.Iterator(img):
                if not frametiming:
                    frametiming = frame.info.get("duration", img.info.get("duration", 0))
                frames.append(frame.copy().convert("RGB"))

        widths, heights = zip(*(f.size for f in frames))
        total_width = max(widths)
        total_height = sum(heights)
        combined = Image.new("RGB", (total_width, total_height))
        y_offset = 0

        for frame in frames:
            combined.paste(frame, (0, y_offset))
            y_offset += frame.height

        if trans:
            combined_p = combined.convert("P", palette=Image.ADAPTIVE, colors=num_colors-1, dither=Image.NONE)

            pal = combined_p.getpalette()
            pal = [255, 0, 255] + pal
            combined_p.putpalette(pal)
        else:
            combined_p = combined.convert("P", palette=Image.ADAPTIVE, colors=num_colors-1, dither=Image.NONE)

        frames_p = []
        for frame in frames:
            f_p = frame.quantize(palette=combined_p, dither=Image.NONE)
            if trans:
                f_p.info["transparency"] = 0
            frames_p.append(f_p)

        raw_palette = combined_p.getpalette()[:num_colors*3]
        seen = set()
        palette = [tuple(raw_palette[i:i+3]) for i in range(0, len(raw_palette), 3) if not (tuple(raw_palette[i:i+3]) in seen or seen.add(tuple(raw_palette[i:i+3])))]

        return frames_p, palette, frametiming, trans
    else:
        if trans == 2 or num_colors > 256 or prepalette:
            img, palette = quantize_most_frequent(img, num_colors, prepalette, dodithering)
            if trans != 2:
                palette_na = []
                for col in palette:
                    palette_na.append((col[0], col[1], col[2]))
                palette = palette_na
        else:
            if dodithering:
                if trans == 0:
                    img = img.convert("RGB")
                    pal = img.quantize(num_colors)
                    img = img.quantize(num_colors, palette=pal, dither=Image.FLOYDSTEINBERG)
                else:
                    img = pillow_kinda_sucks(img, num_colors)
            else:
                img = img.convert("P", palette=Image.ADAPTIVE, colors=num_colors, dither=Image.NONE) # disable dithering to reduce file sizes

            # get the palette as tuples
            raw_palette = img.getpalette()[:num_colors*3]
            seen = set()
            palette = [c for c in (tuple(raw_palette[i:i+3]) for i in range(0, len(raw_palette), 3)) if not (c in seen or seen.add(c))]

        return img, palette, None, trans

def pillow_kinda_sucks(img, num_colors):
    alpha = img.getchannel("A")
    bg = Image.new("RGBA", img.size, (255, 0, 255, 255))
    rgb = Image.alpha_composite(bg, img)
    rgb = rgb.convert("RGB")

    pal = img.quantize(num_colors)
    pal = pal.getpalette()
    pal = [255, 0, 255] + pal

    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal)

    img2 = rgb.quantize(num_colors, palette=pal_img, dither=Image.FLOYDSTEINBERG)

    transparent_index = 0

    pixels = img2.load()
    alpha_pixels = alpha.load()

    for y in range(img2.height):
        for x in range(img2.width):
            if alpha_pixels[x, y] == 0:
                pixels[x, y] = transparent_index

    img2.info["transparency"] = transparent_index
    return img2

def reduce_to_apf_in_apf2_quality(img: Image, animated: bool = False):
    if animated:
        frames = []
        frametiming = None

        for frame in ImageSequence.Iterator(img):
            frametiming = frame.info.get("duration", img.info.get("duration", 0))
            bw = frame.convert("1")  # 1-bit black/white
            frames.append(bw)

        return frames, frametiming
    else:
        img = img.convert("1")
        return img, None


def generate_runs_apf2_l(bitmap: list, lineskip: int, w: int, h: int, topside_first: bool = False, bg = False, trans: int = 0):
    runcounter = 0
    if trans == 2:
        currentrun = bg
    elif bg and type(bg) == tuple:
        currentrun = bg[0:3]
    else:
        currentrun = False
    runlens = []
    n = 0

    revmap = order_pixels(bitmap, h, lineskip, topside_first)

    for vline in revmap:
        for pixel in vline:
            if trans != 2 and type(pixel) == tuple:
                pixel = pixel[0:3]
            if currentrun == pixel:
                if runcounter+1 > 94:
                    runlens.append(runcounter)
                    runlens.append(0)
                    runcounter = 0
                runcounter += 1
            else:
                runlens.append(runcounter)
                runcounter = 1
                currentrun = pixel
    if runcounter > 0:
        runlens.append(runcounter)
    return runlens

def uint8_to_base95_with_corrector(val):
    d = mapping[val]
    c = mapping.index(d)
    e = val - c
    return d, e

# this orders the pixels to be in scan order
def order_pixels(bitmap, h, lineskip, topside_first):
    revmap = []
    passoffset = 0
    if topside_first:
        curline = 0
    else:
        curline = h-1

    for i in range(h):
        revmap.append(bitmap[curline])
        if topside_first:
            curline += lineskip
            if curline > h-1:
                passoffset +=1
                curline = passoffset
        else:
            curline -= lineskip
            if curline < 0:
                passoffset +=1
                curline = h-1-passoffset

    return revmap

def generate_runs_apf2_f(bitmap: list, lineskip: int, w: int, h: int, trans, compress: bool, topside_first: bool, mode: int, combine: bool = False, prevframe: list = None, avoid_run_breaks: bool = False, transmag: bool = False):
    if mode <3: # heart
        raise ValueError("Modes 0, 1, and 2 should not be flex encoded!")

    # defaults to off
    gray = False
    perfect = False
    alpha = False
    fakealpha = False

    if mode in (7, 8):
        gray = True
        if mode == 8:
            perfect = True

    if mode in (5, 6):
        perfect = True

    if mode in (4, 6):
        alpha = True

    if mode == 5 and trans:
        fakealpha = True

    runcounter = 0
    currentrun = None
    runlens = []

    revmap = order_pixels(bitmap, h, lineskip, topside_first)
    prevrev = None
    if prevframe:
        prevrev = order_pixels(prevframe, h, lineskip, topside_first)

    # modes:
    # 0 - 2 colors
    # 1 - 95 colors
    # 2 - 9025 colors
    # 3 - near-truecolor
    # 4 - near-truecolor with alpha
    # 5 - truecolor
    # 6 - truecolor with alpha
    # 7 - Mode 1-based Grayscale
    # 8 - Mode 2-based Grayscale

    transtuples = ("    ", "     ") # 4 spaces is for m4 and m5+t, 5 spaces is for m6
    if transmag:
        transtuples = ("    ", "     ", "~ ~")

    for y in range(h):
        for x in range(w):
            isTransPix = False
            pixel = revmap[y][x]
            if prevrev:
                if not avoid_run_breaks or (not (runcounter>1 and not currentrun in transtuples)):
                    if pixel == prevrev[y][x]:
                        pixel = (255, 0, 255) if transmag else (0,0,0,0)
                        isTransPix = True

            if gray:
                pixtup = (pixel[0]+pixel[0]+pixel[1]+pixel[1]+pixel[1]+pixel[2])//6 # 2xR, 3xG, 1xB
                if perfect:
                    i0, i1 = pixtup%95, pixtup//95
                    ind = chr(i1+32)+chr(i0+32)
                    curpixval = ind
                else:
                    v, _ = uint8_to_base95_with_corrector(pixtup)
                    curpixval = v

            else:
                if combine and pixel == (0,0,0,0) and not isTransPix:
                    pixel = (255,0,255,0) # alpha is zero but the RGB is non-zero

                r, rc = uint8_to_base95_with_corrector(pixel[0])
                g, gc = uint8_to_base95_with_corrector(pixel[1])
                b, bc = uint8_to_base95_with_corrector(pixel[2])
                a, ac = "~", 0

                if alpha:
                    a, ac = uint8_to_base95_with_corrector(pixel[3])

                # tri-level alpha for free
                elif fakealpha and perfect:
                    if pixel[3] >= 176:
                        ac = 2
                    elif pixel[3] <= 80:
                        ac = 0
                    else:
                        ac = 1

                cval = ((rc)+(gc*3)+(bc*9)+(ac*27))
                c = chr(cval+32)

                ccol = [r, g, b]
                if alpha:
                    ccol.append(a)
                if perfect:
                    ccol.append(c)

                curpixval = "".join(ccol)
                if not isTransPix and (transmag and curpixval == "~ ~"):
                    curpixval = "~!~"

            if currentrun == curpixval:
                if (runcounter+1 > 94) or (not compress): # dont compress
                    if currentrun is not None:
                        runlens.append([curpixval, runcounter])
                    currentrun = curpixval
                    runcounter = 0

                runcounter += 1

            else:
                if currentrun is not None:
                    runlens.append([currentrun, runcounter])
                runcounter = 1
                currentrun = curpixval

    if runcounter > 0:
        if trans and currentrun[3] == 0:
            currentrun = (0,0,0,0)
        runlens.append([curpixval, runcounter])

    rldb = []
    for rl in runlens:
        rldb.append(rl[1])
    total = sum(rldb)
    return runlens

def generate_runs_apf2(bitmap: list, palette: list, lineskip: int, w: int, h: int, trans = 0, dim: bool = False, prepalette: str = None, compress: bool = True, topside_first: bool = False, palette_only: bool = False, combine: bool = False, prevframe: list = None, avoid_run_breaks: bool = False):
    trans = int(trans)
    colpal = {}
    colpalbnr = {}
    reservespace = False
    if not (len(palette) == 95 or len(palette) == 9025):
        reservespace = True

    if prepalette:
        apf2pal = prepalette
        colpal = apf2palettedecode(prepalette, dim, bool(trans == 2), False)

        for key in colpal:
            colpalbnr[colpal[key]] = key

        if trans == 1:
            if dim:
                colpalbnr[(0, 0, 0, 0)] = "  "
                colpalbnr[(255, 0, 255, 0)] = "  "
            else:
                colpalbnr[(0, 0, 0, 0)] = " "
                colpalbnr[(255, 0, 255, 0)] = " "

    else:
        if dim:
            for i in range(0,len(palette)):
                oi = i
                if reservespace:
                    i+=1
                pid = chr((i//95)+32)
                pid += chr((i%95)+32)
                colpal[pid] = palette[oi]
        else:
            for i in range(0,len(palette)):
                colpal[chr(i+32+int(reservespace))] = palette[i]

        if trans == 1:
            for key in colpal:
                kreisi = list(colpal[key])
                kreisi.append(255)
                kreisi = tuple(kreisi)
                colpalbnr[kreisi] = key
            if dim:
                colpalbnr[(0, 0, 0, 0)] = "  "
                colpalbnr[(255, 0, 255, 0)] = "  "
            else:
                colpalbnr[(0, 0, 0, 0)] = " "
                colpalbnr[(255, 0, 255, 0)] = " "
        else:
            for key in colpal:
                colpalbnr[colpal[key]] = key

        apf2pal_array = []
        apf2pal = ""
        for col in colpal:
            if trans == 2:
                r, g, b, a = colpal[col]
                liberal = (f"{r:02X}", f"{g:02X}", f"{b:02X}", f"{a:02X}")
                apf2pal_array.append(f"{col}{''.join(liberal)}")
            else:
                r, g, b = colpal[col]
                liberal = (f"{r:02X}", f"{g:02X}", f"{b:02X}")
                apf2pal_array.append(f"{col}{''.join(liberal)}")

        apf2pal = ''.join(apf2pal_array)

        if palette_only: # Moderate optimization
            return None, apf2pal

    runcounter = 0
    currentrun = None
    runlens = []

    revmap = order_pixels(bitmap, h, lineskip, topside_first)
    prevrev = None
    if prevframe:
        prevrev = order_pixels(prevframe, h, lineskip, topside_first)

    for y in range(h):
        for x in range(w):
            pixel = revmap[y][x]
            if prevrev:
                if not avoid_run_breaks or (not (runcounter>1 and not currentrun == (0,0,0,0))):
                    if pixel == prevrev[y][x]:
                        pixel = (0,0,0,0)

            if currentrun == pixel:
                if (runcounter+1 > 94) or (not compress): # dont compress
                    if currentrun is not None:
                        if not currentrun in colpalbnr:
                            if not currentrun[3] == 255:
                                currentrun = (255, 0, 255, 0)
                        runlens.append([colpalbnr[currentrun], runcounter])
                    currentrun = pixel
                    runcounter = 0
                runcounter += 1
            else:
                if currentrun is not None:
                    if trans and currentrun[3] == 0:
                        currentrun = (0,0,0,0)
                    if not currentrun in colpalbnr:
                        runlens.append([" ", runcounter])
                    else:
                        runlens.append([colpalbnr[currentrun], runcounter])
                runcounter = 1
                currentrun = pixel
    if runcounter > 0:
        if trans and currentrun[3] == 0:
            currentrun = (0,0,0,0)
        runlens.append([colpalbnr[currentrun], runcounter])

    rldb = []
    for rl in runlens:
        rldb.append(rl[1])
    total = sum(rldb)
    return runlens, apf2pal

# wrapper function to encode the data
def encode_wrapper(legacy, bitmaps, gray, truecolor, lineskip, w, h, topside_first, bg, trans, avoid_run_breaks, transmag, mode, combine, palette, dim, prepalette, compress):
    apf2pal = None

    if legacy:
        outputs = []
        for bitmap in bitmaps:
            temp = []
            runlens = generate_runs_apf2_l(bitmap, lineskip, w, h, topside_first, bg, trans)
            for num in runlens:
                temp.append(chr(num+32))
            tempstr = "".join(temp)
            temp = None
            outputs.append(tempstr)
        output = "\n".join(outputs)

    elif gray or truecolor:
        outputs = []
        for bm in range(len(bitmaps)):
            temp = []
            prevframe = None
            if bm != 0 and combine:
                prevframe = bitmaps[bm-1]

            runlens = generate_runs_apf2_f(bitmaps[bm], lineskip, w, h, trans, compress, topside_first, mode, combine, prevframe, avoid_run_breaks, transmag)
            for num in runlens:
                temp.append(num[0])
                if compress:
                    temp.append(chr(num[1]+32))

            tempstr = "".join(temp)
            temp = None
            outputs.append(tempstr)

        output = "\n".join(outputs)

    else:
        outputs = []
        _, apf2pal = generate_runs_apf2(bitmaps[0], palette, lineskip, w, h, trans, dim, prepalette, compress, topside_first, True)

        for bm in range(len(bitmaps)):
            temp = []
            prevframe = None
            if bm != 0 and combine:
                prevframe = bitmaps[bm-1]

            runlens, _ = generate_runs_apf2(bitmaps[bm], palette, lineskip, w, h, trans, dim, prepalette, compress, topside_first, False, combine, prevframe, avoid_run_breaks)
            for num in runlens:
                temp.append(num[0])
                if compress:
                    temp.append(chr(num[1]+32))

            tempstr = "".join(temp)
            temp = None
            outputs.append(tempstr)

        output = "\n".join(outputs)

        if trans == 1:
            if dim:
                apf2pal = "  FF00FF"+apf2pal
            else:
                apf2pal = " FF00FF"+apf2pal # this is for decoders without transparency support

    return output, apf2pal

def encode(img: bytes | Image.Image, lineskip: int = None, findbestlineskip: bool = False, legacy: bool = False, trans = False, pal: int = 95, desc: str = "", prepalette: str = None, dodithering: bool = False, returnbytes: bool = False, compress: bool = True, topside_first: bool = False, emit_redundant_flag: bool = False, mode: int = None, combine: bool = False, avoid_run_breaks: bool = False, width: int = None, height: int = None):
    frametiming = None
    bakedpal = None
    dim = False
    transmag = False

    trans = int(trans) # compatability filter
    if trans > 2:
        raise Exception("Error: Invalid Transparency Mode!")

    if mode and mode > 8:
        raise Exception("Error: Invalid Mode!")

    if combine and mode == 3:
        transmag = True
    elif combine and trans == 0:
        trans = 1

    find_bgfg = False
    bgfg = None
    bg = False # needed
    palette = None

    if pal == 2 and mode in (None, 0):
        legacy = True
        find_bgfg = True

    gray = False
    truecolor = False

    if findbestlineskip and lineskip == None:
        print("Warning: findbestlineskip enabled and no lineskip provided, setting max pass check to 10")
        lineskip = 10

    if lineskip is None:
        lineskip = 1

    if pal > 95:
        dim = True
        if pal > 9025:
            raise Exception("Error: Palette cannot be larger than 9025 colors!")

    if not legacy and mode == 0:
        legacy = True
    if mode == 2:
        dim = True

    if mode == 7:
        gray = 1
    if mode == 8:
        gray = 2

    if combine and gray:
        print("Warning: You cannot use combine with grayscale images")
        combine = False
        trans = 0

    if legacy:
        combine = False

    if mode in (3, 4, 5, 6):
        truecolor = True

    if mode in (4, 6):
        trans = 2

    if legacy and prepalette:
        raise Exception("Error: Legacy mode cannot be used in conjunction with a pre-baked palette!")

    if legacy and not compress:
        raise Exception("Error: Legacy mode cannot be uncompressed!")

    if prepalette:
        if dim:
            if trans == 2:
                bakedpal = apf2palettedecode(prepalette, True, True, True)
            else:
                bakedpal = apf2palettedecode(prepalette, True, False, True)
        else:
            if trans == 2:
                bakedpal = apf2palettedecode(prepalette, False, True, True)
            else:
                bakedpal = apf2palettedecode(prepalette, False, False, True)

    if trans == 1 and (pal == 95) and (not mode == 2):
        pal = 94
    if trans == 1 and (pal == 9025):
        pal = 9024

    if type(img) == bytes:
        img = Image.open(io.BytesIO(img))

    w, h = img.size

    # preserve aspect ratio modes
    if width is not None and height is None:
        aspct = h/w
        height = round(width*aspct)
    if width is None and height is not None:
        aspct = w/h
        width = round(height*aspct)

    if width is not None and height is not None:
        img = img.resize((width, height))
        w, h = img.size

    animated = getattr(img, "is_animated", False)
    if legacy and not find_bgfg:
        img, frametiming = reduce_to_apf_in_apf2_quality(img, animated)
    elif not truecolor and not gray:
        img, palette, frametiming, trans = reduce_to_apf2_quality(img, pal, animated, trans, bakedpal, dodithering)
    else:
        img, frametiming = slice_frames(img, animated, trans)

    if find_bgfg:
        mod = "RGB"
        if trans:
            mod += "A"
        if type(img) is list:
            img_rgb = img[0].convert(mod)
        else:
            img_rgb = img.convert(mod)
        pixacc = img_rgb.load()

        bg = pixacc[0, 0]
        fg = None
        stop = False

        for y in range(h):
            for x in range(w):
                if pixacc[x, y] != bg:
                    fg = pixacc[x, y]
                    break

            if fg is not None:
                break

        if fg is None:
            fg = (255, 255, 255)
        bgfg = (bg, fg)

    imageData = io.StringIO()

    uses2000extensions = (not compress or topside_first or emit_redundant_flag or gray or combine or truecolor)

    uses1994extensions = (trans == 2 or dim)

    if uses2000extensions:
        apflist = [apf2headertext2000]
    elif uses1994extensions:
        apflist = [apf2headertext1994]
    else:
        apflist = [apf2headertext]

    metadata = []
    frames = []
    if animated:
        for image in img:
            if legacy:
                frames.append(image.load())
            else:
                frames.append(image)
        #pixels = frames[0]
        res = img[0].size
    else:
        pixels = img.load()
        res = img.size
    metadata.append(f"{res[0]}x{res[1]}")

    args = ""
    if legacy:
        args+="l"
    if trans == 1:
        args+="t"
    if animated:
        args+="m"

    if trans == 2:
        args+="a"
    if dim:
        args+="d"

    if not compress:
        args+="U"
    if topside_first:
        args+="u"
    if emit_redundant_flag and (not (legacy or dim)):
        args+="i"
    if combine:
        args+="c"
    if transmag:
        args+="M"

    if gray == 1:
        args+="g"
    if gray == 2:
        args+="G"

    if mode == 3:
        args+="q"
    if mode == 4:
        args+="n"
    if mode == 5:
        args+="T"
    if mode == 6:
        args+="A"

    metadata.append(args)
    if not findbestlineskip:
        metadata.append(str(lineskip))

    if legacy and not bgfg:
        if animated:
            bitmaps = []
            for pixels in frames:
                bitmaps.append([[pixels[x, y] != 0 for x in range(w)] for y in range(h)])
        else:
            bitmap = [[pixels[x, y] != 0 for x in range(w)] for y in range(h)]
    else:
        colmode = "RGB"
        if trans:
            colmode+="A"

        if animated:
            bitmaps = []
            for img in frames:
                if type(img) == Image.Image:
                    img_rgb = img.convert(colmode)
                    pixels = img_rgb.load()
                else:
                    pixels = img
                if trans == 1:
                    bitmaps.append([[(*pixels[x, y][:3], 255 if pixels[x, y][3] > 0 else 0) for x in range(w)] for y in range(h)])
                else:
                    bitmaps.append([[pixels[x, y] for x in range(w)] for y in range(h)])
        else:
            img_rgb = img.convert(colmode)
            pixels = img_rgb.load()
            if trans == 1:
                bitmap = [[(*pixels[x, y][:3], 255 if pixels[x, y][3] > 0 else 0) for x in range(w)] for y in range(h)]
            else:
                bitmap = [[pixels[x, y] for x in range(w)] for y in range(h)]

        img_rgb = None # take out the trash
        pixels = None
        frames = None

    output = ""

    if not animated:
        bitmaps = [bitmap]

    if findbestlineskip:
        all_outputs = {}
        apf2pal = None
        outsize = float('inf')
        if lineskip >= h:
            lineskip = h-1

        for lsk in range(lineskip):
            lsk+=1
            output, apf2pal = encode_wrapper(legacy, bitmaps, gray, truecolor, lsk, w, h, topside_first, bg, trans, avoid_run_breaks, transmag, mode, combine, palette, dim, prepalette, compress)
            all_outputs[str(lsk)] = output
        for lsk in all_outputs:
            if outsize > len(all_outputs[lsk])+len(lsk):
                output = all_outputs[lsk]
                outsize = len(all_outputs[lsk])+len(lsk)
                lineskip = int(lsk)
        metadata.append(str(lineskip))
    else:
        output, apf2pal = encode_wrapper(legacy, bitmaps, gray, truecolor, lineskip, w, h, topside_first, bg, trans, avoid_run_breaks, transmag, mode, combine, palette, dim, prepalette, compress)


    if desc or frametiming:
        metadata.append(desc)
    if frametiming:
        metadata.append(str(frametiming))

    metadata = ",".join(metadata)
    apflist.append(metadata)

    if gray or truecolor:
        apflist.append(".")
    elif legacy:
        if bgfg:
            if trans == 2:
                bg = f"{bgfg[0][0]:02X}{bgfg[0][1]:02X}{bgfg[0][2]:02X}{bgfg[0][3]:02X}"
                fg = f"{bgfg[1][0]:02X}{bgfg[1][1]:02X}{bgfg[1][2]:02X}{bgfg[1][3]:02X}"
            else:
                if trans == 1:
                    bg = ""
                else:
                    bg = f"{bgfg[0][0]:02X}{bgfg[0][1]:02X}{bgfg[0][2]:02X}"
                fg = f"{bgfg[1][0]:02X}{bgfg[1][1]:02X}{bgfg[1][2]:02X}"
            apflist.append(f"{bg}.{fg}")
        else:
            apflist.append(".")
    else:
        apflist.append(apf2pal)

    apflist.append(output)
    apftext = "\n".join(apflist)
    if returnbytes:
        return apftext.encode()
    else:
        return apftext
