import io, textwrap, os, math
from PIL import Image, ImageSequence, ImageOps

def bitstring_to_bytes(s):
    s = s.replace(" ", "")
    s = s.replace(",", "")
    s = s.replace("_", "")
    return int(s, 2).to_bytes((len(s) + 7) // 8, byteorder='big')
    
def encodeotab(img: Image, width=255, height=255):
    if width > 255 or height > 255:
        raise Exception("Invalid Resolution")
    res = img.size
    
    # don't upscale
    if width > res[0]:
        width = res[0]
    if height > res[1]:
        height = res[1]
    img = img.resize((width, height))
    img = img.convert("1")
    
    pixels = img.load()
    payload = b'\x00' # type 0 hardcoded header
    payload += width.to_bytes(1, 'big')
    payload += height.to_bytes(1, 'big')
    payload += b'\x01' # 1 color hardcoded header
    print(f"header: {payload.hex()}")
    bitmap = [[pixels[x, y] for x in range(img.width)] for y in range(img.height)]

    collection = ""
    cat = 0
    for hline in bitmap:
        for px in hline:
            cat += 1
            if px:
                collection += "0"
            else:
                collection += "1"
            if len(collection) == 8:
                payload += bitstring_to_bytes(collection)
                collection = ""
    if collection:
        payload += bitstring_to_bytes(collection)
        collection = ""
        cat = 0

    return payload

def decodeotab(otab: bytes, format: str = 'PNG', returnImageObject: bool = False):
    w = 0
    h = 0
    it = 0
    
    headeryeah = False
    img = None
    for byte in otab:
        if headeryeah:
            for p in range(0, 8):
                bit = (byte >> (7 - p)) & 1
                x = it % w
                y = it // w
                if 0 <= x < w and 0 <= y < h:
                    pixels[x, y] = not bit
                it += 1
        else:
            it += 1
            if it == 1:
                if not byte == 0:
                    raise Exception("Invalid or unsupported Otb!")
            elif w == 0:
                w = byte
            elif h == 0:
                h = byte
                img = Image.new("1", (w, h))
                pixels = img.load()
            elif it == 4:
                if byte != 1:
                    raise Exception("Invalid or unsupported Otb!")
                else:
                    headeryeah = True
                    it = 0
                    
    if returnImageObject:
        return img
    else:
        imageData = io.BytesIO()
        img.save(imageData, format=format)
        imageData = imageData.getvalue()
        return imageData

