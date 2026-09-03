from .bittools import byte_to_boollist, boollist_to_int_var, mk_uintvar, generate_boollist
from . import scqoi

from PIL import Image
import io

def generate_frame(bitmap: list, palette: list, delay: int, disposal: bool):
    indmap = bytearray()
    for row in bitmap:
        for pixel in row:
            #try:
            indmap.append(palette.index(pixel))
            #except Exception:
            #    indmap.append(0)
    compressed = scqoi.compress(bytes(indmap))
    payloadlength = len(compressed)
    frame = bytearray()
    frame.append(int(disposal))
    frame.extend(delay.to_bytes(2, 'little'))
    frame.extend(payloadlength.to_bytes(4, 'little'))
    frame.extend(compressed)
    return frame

def generateheader(width, height, palette, transmode):
    head = bytearray()
    head.extend(width.to_bytes(2, 'little'))
    head.extend(height.to_bytes(2, 'little'))
    palbytes = bytearray()
    for col in palette:
        palbytes.append(col[0])
        palbytes.append(col[1])
        palbytes.append(col[2])
    head.append(len(palette)-1)
    head.append(int(transmode))

    head.extend(palbytes)

    return head

def gen_palette(bitmap, reserved: tuple = None, animated: bool = False):
    pal = []
    seen = set()

    if animated:
        imagedata = bitmap
    else:
        imagedata = [bitmap]

    for bitmap in imagedata:
        for row in bitmap:
            for px in row:
                if px not in seen:
                    seen.add(px)
                    pal.append(px)
                    if len(pal) > 256:
                        return "PLEASE QUANTIZE", reserved

    pal.sort(key=lambda c: (c[0], c[1], c[2]))

    if reserved in pal:
        pal.remove(reserved)
        pal.insert(0, reserved)
    elif not reserved is None:
        print("warning, no transparency.")
        reserved = None
    return pal, reserved

def encode(img: list | Image.Image, transcolor: tuple = None):
#def encode(bitmap: list | Image.Image, transcolor: tuple = None, animated: bool = False, disposalmodes: list = None, framedelays: list = None):
    qif = bytearray(b"QIF26a")

    if not type(img) is list:
        img = img.convert("RGB")
        px = img.load()
        pixels = [[px[x, y] for x in range(img.width)] for y in range(img.height)]
        img = pixels

    #if animated:
    #    wid = len(bitmap[0][0])
    #    hei = len(bitmap[0])

    #    if not type(bitmap[0][0][0]) is tuple:
    #        raise Exception("grayscale is unsupported as of now")
    #    if disposalmodes is None or len(bitmap) > len(disposalmodes):
    #        raise Exception("a list of disposal modes for all frames is required!")
    #    if framedelays is None or len(bitmap) > len(framedelays):
    #        raise Exception("a list of timings for all frames is required!")
    #else:
    wid = len(img[0])
    hei = len(img)

    if not type(img[0][0]) is tuple:
        raise Exception("grayscale is unsupported as of now")

    #if animated:
    #    pal, transcolor = gen_palette(bitmap, transcolor, True)
    #else:
    pal, transcolor = gen_palette(img, transcolor, False)
    if pal == "PLEASE QUANTIZE":
        img = Image.new("RGB", (wid, hei))
        img.putdata([pixel for row in pixels for pixel in row])
        img = img.convert("P")
        img = img.convert("RGB")
        px = img.load()
        img = [[px[x, y] for x in range(img.width)] for y in range(img.height)]
        pal, transcolor = gen_palette(img, transcolor, False)

    qif.extend(generateheader(wid, hei, pal, bool(transcolor)))
    #if animated:
    #    for i in range(len(bitmap)):
    #        qif.extend(generate_frame(bitmap[i], pal, framedelays[i], disposalmodes[i]))
    #else:
    qif.extend(generate_frame(img, pal, 0, False))

    qif.extend(b"\x00\x00\x00\x00\x00\x00\x00;")
    return bytes(qif)

def parseheader(header: bytes):
    width = int.from_bytes(header[0:2], "little")
    height = int.from_bytes(header[2:4], "little")
    palettesize = int(header[4])+1
    transparency = int(header[5])
    palette = []
    for i in range(palettesize):
        palette.append((int(header[(i*3)+6]), int(header[(i*3)+7]), int(header[(i*3)+8])))

    return width, height, palettesize, transparency, palette

def framebehead(data: bytes):
    disposal = int(data[0])
    delay = int.from_bytes(data[1:3], "little")
    payloadlength = int.from_bytes(data[3:8], "little")
    return disposal, delay, payloadlength

def decode_data(data, palette, transparency, width, height):
    frames = []
    delays = []
    bytten = 0

    while True:
        disposal, delay, payloadlength = framebehead(data[bytten:bytten+7])

        if disposal and not len(frames) == 0:
            imge = frames[-1].copy()
            frame = imge.load()
        else:
            imge = Image.new(mode="RGBA", size=(width, height), color = (0, 0, 0, 0))
            frame = imge.load()

        bytten += 7
        if payloadlength == 0:
            return frames, delays
        else:
            compressed = data[bytten:payloadlength+bytten]
            bytten += payloadlength
            ndata = scqoi.decompress(compressed)
            cx = 0
            cy = 0
            for index in ndata:
                if not (transparency and index == 0):
                    frame[cx, cy] = palette[index]
                cx += 1
                if cx == width:
                    cx = 0
                    cy += 1
                if cy == height:
                    break
            frames.append(imge)
            delays.append(delay)
    return frames, delays

def decode(mqif: bytes, format: str = 'GIF', returnImageObject: bool = False, provide_extra_data: bool = True):
    if not mqif.startswith(b'QIF26a'):
        raise Exception("Invalid QIF Image!")
    header = mqif[6:]
    width, height, palettesize, transparency, palette = parseheader(header)
    data = mqif[12+(palettesize*3):]
    frames, delays = decode_data(data, palette, transparency, width, height)
    if returnImageObject:
        if provide_extra_data:
            if len(frames) > 1:
                return frames, delays
            else:
                return frames[0], None
        else:
            if len(frames) > 1:
                return frames
            else:
                return frames[0]
    else:
        imageData = io.BytesIO()
        if format.lower() == "gif":
            frames[0].save(imageData, format=format, save_all=True, append_images=frames[1:], duration=delays, loop=0, optimize=False, disposal=2)
        elif format.lower() == "webp":
            frames[0].save(imageData, format=format, save_all=True, append_images=frames[1:], duration=delays, loop=0, optimize=False, disposal=2, lossless=True)
        else:
            frames[0].save(imageData, format=format)
        imageData = imageData.getvalue()
        return imageData
