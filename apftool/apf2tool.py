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

def apf2_apfdecodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: list, trans: bool = False):
    x = 0
    y = h-1
    passoffset = 0
    state = False # swapping this will invert the image.

    for char in data:
        runlen = ord(char) - 32
        for i in range(runlen):
            if 0 <= y < len(apfbuffer) and 0 <= x < len(apfbuffer[0]):
                apfbuffer[y][x] = (state)
            x += 1
            if not x < w:
                y = y - lineskip
                x = 0
            if y < 0:
                y = h-1
                passoffset +=1
                y -= passoffset
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

def apf2decodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: str, trans = 0):
    x = 0
    y = h-1
    passoffset = 0

    # convert palette to dictionary tuples
    istrans2 = bool(trans == 2)

    pal = apf2palettedecode(pals, False, istrans2, False)

    if trans == 1:
        pal[" "] = (0, 0, 0, 0)

    for pair in range(len(data)//2):
        color = data[pair*2]
        runlen = ord(data[pair*2+1]) - 32

        for i in range(runlen):
            if 0 <= y < len(apfbuffer) and 0 <= x < len(apfbuffer[0]):
                apfbuffer[y][x] = pal[color]

            x += 1
            if x >= w:
                y -= lineskip
                x = 0

            if y < 0:
                y = h-1
                passoffset += 1
                y -= passoffset

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

def apf2_1994_decodedata(data: str, h: int, w: int, apfbuffer: list, lineskip: int, pals: str, trans = 0):
    x = 0
    y = h-1
    passoffset = 0

    # convert palette to dictionary tuples
    istrans2 = bool(trans == 2)

    pal = apf2palettedecode(pals, True, istrans2, False)

    if trans == 1:
        pal["  "] = (0, 0, 0, 0)

    for pair in range(len(data)//3):
        color = data[pair*3]+data[(pair*3)+1]
        runlen = ord(data[pair*3+2]) - 32

        for i in range(runlen):
            if 0 <= y < len(apfbuffer) and 0 <= x < len(apfbuffer[0]):
                apfbuffer[y][x] = pal[color]

            x += 1
            if x >= w:
                y -= lineskip
                x = 0

            if y < 0:
                y = h-1
                passoffset += 1
                y -= passoffset

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

def decodeapf2(apf2: str | bytes, format: str = 'PNG', returnImageObject: bool = False):
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

    if not apf_lines[0].strip() == apf2headertext and not apf_lines[0].strip() == apf2headertext1994:
        raise Exception("Invalid Aperture Image Format File")
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

    if "l" in arguments:
        mode = "legacy"
    elif "d" in arguments:
        mode = "apf2-1994"
    else:
        mode = "apf2"

    if "m" in arguments:
        datatype = "multistream"
        data = apf_lines[3:]
    else:
        datatype = "singlestream"
        data = apf_lines[3]
    istrans = int(("t" in arguments))
    if not istrans:
        istrans = int(("a" in arguments))*2

    apfbuffer = []
    for i in range((h)):
        row = []
        for e in range((w)):
            row.append(None)
        apfbuffer.append(row)

    imgs = []
    if datatype == "multistream":
        if mode == "legacy":
            pals = apf_lines[2].split(".")
            if pals[0] == "":
                if istrans == 1:
                    pals[0] = (0,0,0,0)
                else:
                    pals[0] = (0,0,0)
            else:
                hexcsegment = textwrap.wrap(pals[0], 2)
                pals[0] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))
            if pals[1] == "":
                pals[1] = (255,255,255)
            else:
                hexcsegment = textwrap.wrap(pals[1], 2)
                pals[1] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

            for ds in data:
                imgs.append(apf2_apfdecodedata(ds, h, w, apfbuffer, lineskip, pals, istrans))
        elif mode == "apf2-1994":
            pals = apf_lines[2]
            for ds in data:
                imgs.append(apf2_1994_decodedata(ds, h, w, apfbuffer, lineskip, pals, istrans))
        else:
            pals = apf_lines[2]
            for ds in data:
                imgs.append(apf2decodedata(ds, h, w, apfbuffer, lineskip, pals, istrans))
        imageData = io.BytesIO()
        imgs[0].save(
            imageData,
            format="GIF",
            save_all=True,
            append_images=imgs[1:],
            loop=0,
            duration=delay,
            disposal=2
        )
        imageData = imageData.getvalue()
    else:
        if mode == "legacy":
            pals = apf_lines[2].split(".")
            if pals[0] == "":
                if istrans == 1:
                    pals[0] = (0,0,0,0)
                else:
                    pals[0] = (0,0,0)
            else:
                hexcsegment = textwrap.wrap(pals[0], 2)
                pals[0] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))
            if pals[1] == "":
                pals[1] = (255,255,255)
            else:
                hexcsegment = textwrap.wrap(pals[1], 2)
                pals[1] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

            img = apf2_apfdecodedata(data, h, w, apfbuffer, lineskip, pals, istrans)
        elif mode == "apf2-1994":
            pals = apf_lines[2]
            img = apf2_1994_decodedata(data, h, w, apfbuffer, lineskip, pals, istrans)
        else:
            pals = apf_lines[2]
            img = apf2decodedata(data, h, w, apfbuffer, lineskip, pals, istrans)
    if returnImageObject:
        if datatype == "multistream":
            return imgs # list object, be careful
        else:
            return img
    else:
        if datatype == "multistream":
            imageData = io.BytesIO()
            imgs[0].save(
                imageData,
                format="GIF",
                save_all=True,
                append_images=imgs[1:],
                loop=0,
                duration=delay,
                disposal=2
            )
            imageData = imageData.getvalue()
            return imageData
        else:
            imageData = io.BytesIO()
            img.save(imageData, format=format)
            imageData = imageData.getvalue()
            return imageData

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


def generate_runs_apf2_l(bitmap: list, lineskip: int, w: int, h: int):
    runcounter = 0
    currentrun = False  # swapping this will invert the image as well
    runlens = []
    curline = h-1
    revmap = []
    passoffset = 0
    for i in range(h):
        revmap.append(bitmap[curline])
        curline -= lineskip
        if curline < 0:
            curline = h-1
            passoffset +=1
            curline -= passoffset

    for vline in revmap:
        for pixel in vline:
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

def generate_runs_apf2(bitmap: list, palette: list, lineskip: int, w: int, h: int, trans = 0, dim: bool = False, prepalette: str = None):
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

    runcounter = 0
    currentrun = None
    runlens = []
    curline = h-1
    revmap = []
    passoffset = 0
    for i in range(h):
        revmap.append(bitmap[curline])
        curline -= lineskip
        if curline < 0:
            curline = h-1
            passoffset +=1
            curline -= passoffset

    for vline in revmap:
        for pixel in vline:
            if currentrun == pixel:
                if runcounter+1 > 94:
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

def encodeapf2(img: bytes | Image.Image, lineskip: int = 1, findbestlineskip: bool = False, legacy: bool = False, trans = False, pal: int = 95, desc: str = "", prepalette: str = None, dodithering: bool = False):
    frametiming = None
    bakedpal = None
    dim = False
    trans = int(trans) # compatability filter
    if trans > 2:
        raise Exception("Invalid Transparency Mode!")

    if pal > 95:
        dim = True
        if pal > 9025:
            raise Exception("Palette cannot be larger than 9025 colors!")

    if legacy and prepalette:
        raise Exception("Legacy mode cannot be used in conjunction with a pre-baked palette!")

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

    if trans == 1 and (pal == 95):
        pal = 94
    if trans == 1 and (pal == 9025):
        pal = 9024

    if type(img) == bytes:
        img = Image.open(io.BytesIO(img))

    animated = getattr(img, "is_animated", False)
    if legacy:
        img, frametiming = reduce_to_apf_in_apf2_quality(img, animated)
    else:
        img, palette, frametiming, trans = reduce_to_apf2_quality(img, pal, animated, trans, bakedpal, dodithering)

    imageData = io.StringIO()
    uses1994extensions = (trans == 2 or dim)
    if uses1994extensions:
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
    w = res[0]
    h = res[1]

    args = ""
    if legacy:
        args+="l"
    if trans == 1:
        args+="t"
    if trans == 2:
        args+="a"
    if animated:
        args+="m"
    if dim:
        args+="d"

    metadata.append(args)
    if not findbestlineskip:
        metadata.append(str(lineskip))

    if legacy:
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
                img_rgb = img.convert(colmode)
                pixels = img_rgb.load()
                if trans == 1:
                    bitmaps.append([[(*pixels[x, y][:3], 255 if pixels[x, y][3] > 0 else 0) for x in range(img.width)] for y in range(img.height)])
                else:
                    bitmaps.append([[pixels[x, y] for x in range(img.width)] for y in range(img.height)])
        else:
            img_rgb = img.convert(colmode)
            pixels = img_rgb.load()
            if trans == 1:
                bitmap = [[(*pixels[x, y][:3], 255 if pixels[x, y][3] > 0 else 0) for x in range(img.width)] for y in range(img.height)]
            else:
                bitmap = [[pixels[x, y] for x in range(img.width)] for y in range(img.height)]

        img_rgb = None # take out the trash
        pixels = None
        frames = None

    output = ""
    if findbestlineskip and not animated: # animated images may be wildly inconsistant, and computing them all would take a really long time for what is a small efficiency gain in file size.
        lens = {}
        shortestId = None
        shortestlen = float('inf')
        maxrange = lineskip
        if h-1 < lineskip:
            maxrange = h-1
        for i in range(1, maxrange):
            lens[str(i)] = None
        for ls in lens:
            if legacy:
                lens[ls] = generate_runs_apf2_l(bitmap, int(ls), w, h)
            else:
                lens[ls], apf2pal = generate_runs_apf2(bitmap, palette, int(ls), w, h, trans, dim, prepalette)
        for ls in lens:
            totallen = len(lens[ls])+len(str(ls))
            if totallen < shortestlen:
                shortestlen = totallen
                shortestId = ls
        runlens = lens[shortestId]
        metadata.append(str(shortestId))

        if legacy:
            temp = []
            apf2pal = "."
            for num in runlens:
                temp.append(chr(num+32))
            output = "".join(temp)
            temp = None
        else:
            temp = []
            for num in runlens:
                temp.append(num[0])
                temp.append(chr(num[1]+32))
            output = "".join(temp)
            temp = None

        if trans == 1 and not legacy:
            if dim:
                apf2pal = "  FF00FF"+apf2pal
            else:
                apf2pal = " FF00FF"+apf2pal # this is for decoders without transparency support
    else:
        if animated:
            if legacy:
                outputs = []
                for bitmap in bitmaps:
                    temp = []
                    runlens = generate_runs_apf2_l(bitmap, lineskip, w, h)
                    for num in runlens:
                        temp.append(chr(num+32))
                    tempstr = "".join(temp)
                    temp = None
                    outputs.append(tempstr)
                output = "\n".join(outputs)
            else:
                outputs = []
                _, apf2pal = generate_runs_apf2(bitmaps[0], palette, lineskip, w, h, trans, dim, prepalette)
                for bitmap in bitmaps:
                    temp = []
                    runlens, _ = generate_runs_apf2(bitmap, palette, lineskip, w, h, trans, dim, prepalette)
                    for num in runlens:
                        temp.append(num[0])
                        temp.append(chr(num[1]+32))
                    tempstr = "".join(temp)
                    temp = None
                    outputs.append(tempstr)

                output = "\n".join(outputs)

                if trans == 1 and not legacy:
                    if dim:
                        apf2pal = "  FF00FF"+apf2pal
                    else:
                        apf2pal = " FF00FF"+apf2pal # this is for decoders without transparency support
        else:
            if legacy:
                runlens = generate_runs_apf2_l(bitmap, lineskip, w, h)
                temp = []
                for num in runlens:
                    temp.append(chr(num+32))
                output = "".join(temp)
                temp = None
            else:
                runlens, apf2pal = generate_runs_apf2(bitmap, palette, lineskip, w, h, trans, dim, prepalette)
                if trans == 1 and not legacy:
                    if dim:
                        apf2pal = "  FF00FF"+apf2pal
                    else:
                        apf2pal = " FF00FF"+apf2pal # this is for decoders without transparency support
                temp = []
                for num in runlens:
                    temp.append(num[0])
                    temp.append(chr(num[1]+32))
                output = "".join(temp)
                temp = None
    if desc or frametiming:
        metadata.append(desc)
    if frametiming:
        metadata.append(str(frametiming))

    metadata = ",".join(metadata)
    apflist.append(metadata)

    if legacy:
        apflist.append(".")
    else:
        apflist.append(apf2pal)

    apflist.append(output)
    apftext = "\n".join(apflist)
    return apftext

decodeaf2 = decodeapf2 # compat stubs
encodeaf2 = encodeapf2 # compat stubs
