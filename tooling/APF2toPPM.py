import textwrap

# width and height are 320x200 for standard apf files
af2headertext = "APERTURE IMAGE FORMAT (c) 1993" # af2 header
af2headertext1994 = "APERTURE IMAGE FORMAT (c) 1994" # af2 header (1994 extensions of d, and a)

def af2_apfdecodedata(data: str, h: int, w: int, lineskip: int, pals: list, trans: bool = False):
    apfbuffer = []
    for i in range((h)):
        row = []
        for e in range((w)):
            row.append(None)
        apfbuffer.append(row)

    x = 0
    y = h-1
    passoffset = 0
    state = False # swapping this will invert the image.

    for char in data:
        runlen = ord(char) - 32
        for i in range(runlen):
            if 0 <= y < len(apfbuffer) and 0 <= x < len(apfbuffer[0]):
                if state:
                    apfbuffer[y][x] = pals[1]
                else:
                    apfbuffer[y][x] = pals[0]
            x += 1
            if not x < w:
                y = y - lineskip
                x = 0
            if y < 0:
                y = h-1
                passoffset +=1
                y -= passoffset
        state = not state

    return apfbuffer

def af2decodedata(data: str, h: int, w: int, lineskip: int, pals: str, trans = 0):
    apfbuffer = []
    for i in range((h)):
        row = []
        for e in range((w)):
            row.append(None)
        apfbuffer.append(row)

    x = 0
    y = h-1
    passoffset = 0

    # convert palette to dictionary tuples
    seven = 7
    if trans == 2:
        seven = 9

    palsegments = textwrap.wrap(pals, seven)
    pal = {}
    if trans == 2:
        for col in palsegments:
            ind = col[0]
            hexcs = col[1:]
            hexcsegment = textwrap.wrap(hexcs, 2)
            pal[ind] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16),int(hexcsegment[3], 16))
    else:
        for col in palsegments:
            ind = col[0]
            hexcs = col[1:]
            hexcsegment = textwrap.wrap(hexcs, 2)
            pal[ind] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

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

    return apfbuffer

def af2_1994_decodedata(data: str, h: int, w: int, lineskip: int, pals: str, trans = 0):
    apfbuffer = []
    for i in range((h)):
        row = []
        for e in range((w)):
            row.append(None)
        apfbuffer.append(row)

    x = 0
    y = h-1
    passoffset = 0

    # convert palette to dictionary tuples
    eight = 8
    if trans == 2:
        eight = 10

    palsegments = [pals[i:i+eight] for i in range(0, len(pals), eight)] # text wrap strips whitespace in the middle of data
    pal = {}
    if trans == 2:
        for col in palsegments:
            ind = col[:2]
            hexcs = col[2:]
            hexcsegment = textwrap.wrap(hexcs, 2)
            pal[ind] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16),int(hexcsegment[3], 16))
    else:
        for col in palsegments:
            ind = col[:2]
            hexcs = col[2:]
            hexcsegment = textwrap.wrap(hexcs, 2)
            pal[ind] = (int(hexcsegment[0], 16),int(hexcsegment[1], 16),int(hexcsegment[2], 16))

    if trans == 2:
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

    return apfbuffer

def decodeaf2(af2: str, format: str = None, returnImageObject: bool = False, returnFrames: bool = False):
    if not format in (None, "PPM", "PAM"):
        raise Exception("Unsupported Format!")

    apf_list = af2.splitlines()
    apf_lines = []
    for line in apf_list:
        if line:
            apf_lines.append(line)
    if apf_lines[0].strip() == "APERTURE IMAGE FORMAT (c) 1985": # on the fly af2 upgrade
        af2 = f"APERTURE IMAGE FORMAT (c) 1993\n320x200,l,{apf_list[1]}\n.\n{apf_list[2]}"
        apf_lines = af2.splitlines()

    if not apf_lines[0].strip() == af2headertext and not apf_lines[0].strip() == af2headertext1994:
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

    if format is None:
        if istrans:
            format = "PAM"
        else:
            format = "PPM"

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
                imgs.append(af2_apfdecodedata(ds, h, w, lineskip, pals, istrans))

        elif mode == "apf2-1994":
            pals = apf_lines[2]
            for ds in data:
                imgs.append(af2_1994_decodedata(ds, h, w, lineskip, pals, istrans))
        else:
            pals = apf_lines[2]
            for ds in data:
                dcod = af2decodedata(ds, h, w, lineskip, pals, istrans)
                imgs.append(dcod)
        #img = imgs[0]
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
    
            img = af2_apfdecodedata(data, h, w, lineskip, pals, istrans)
        elif mode == "apf2-1994":
            pals = apf_lines[2]
            img = af2_1994_decodedata(data, h, w, lineskip, pals, istrans)
        else:
            pals = apf_lines[2]
            img = af2decodedata(data, h, w, lineskip, pals, istrans)
        imgs = [img]
    
    if returnFrames:
        if returnImageObject:
            return imgs
        else:
            imageDatas = []
            if format == "PAM":
                for frame in imgs:
                    imageDatas.append(pam_from_list(frame))
            else:
                for frame in imgs:
                    imageDatas.append(ppm_from_list(frame))
            return imageDatas
    else:
        if returnImageObject:
            return img
        else:
            if format == "PAM":
                imageData = pam_from_list(img)
            else:
                imageData = ppm_from_list(img)
            return imageData

def ppm_from_list(bitmap, desc = None):
    ppmhead = "P6\n" # raw format
    ppmbody = bytearray() # byte array

    if desc:
        ppmhead += "# {desc}\n"

    ppmhead += f"{len(bitmap[0])} {len(bitmap)}\n"
    ppmhead += "255\n"

    for row in bitmap:
        for pixel in row:
            ppmbody.append(pixel[0])
            ppmbody.append(pixel[1])
            ppmbody.append(pixel[2])

    return ppmhead.encode() + bytes(ppmbody)

def pam_from_list(bitmap):
    pamhead = f"P7\nWIDTH {len(bitmap[0])}\nHEIGHT {len(bitmap)}\nDEPTH 4\nMAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n" # PAM format
    pambody = bytearray() # byte array

    alpha = False
    if len(bitmap[0][0]) > 3:
        alpha = True

    for row in bitmap:
        for pixel in row:
            pambody.append(pixel[0])
            pambody.append(pixel[1])
            pambody.append(pixel[2])
            if alpha:
                pambody.append(pixel[3])
            else:
                pambody.append(255) # slightly heavier but allows for non-transparent images to output to an RGBA PAM

    return pamhead.encode() + bytes(pambody)

thefile = open('konata.apf2', 'r').read()

decoded = decodeaf2(thefile, returnFrames = True)
i = 0
for ppm in decoded:
    with open(f"frames/konata_{i}.ppm", "wb") as f:
        f.write(ppm)
    i += 1

