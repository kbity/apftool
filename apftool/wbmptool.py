import io, textwrap, os, math
from PIL import Image, ImageSequence, ImageOps

def bitstring_to_bytes(s):
    s = s.replace(" ", "")
    s = s.replace(",", "")
    s = s.replace("_", "")
    return int(s, 2).to_bytes((len(s) + 7) // 8, byteorder='big')

def bitstring_to_int(s):
    s = s.replace(" ", "").replace(",", "").replace("_", "")
    return int(s, 2)
    
def mk_uintvar(num: int):
    chunks = []
    while True:
        chunks.append(num & 0x7F)  # take 7 bits
        num >>= 7
        if num == 0:
            break
    chunks.reverse()
    out = bytearray()
    for i, chunk in enumerate(chunks):
        if i != len(chunks) - 1:
            out.append(0x80 | chunk)  # set continuation bit
        else:
            out.append(chunk)         # last byte
    return bytes(out)

def decode_uintvar(buffer: bytes) -> int:
    value = 0
    for byte in buffer:
        value = (value << 7) | (byte & 0x7F)
    return value
    
def encodewbmp(img: Image):
    img = img.convert("1")
    pixels = img.load()
    res = img.size
    payload = b'\x00\x00' # type 0 hardcoded header
    width = res[0]
    height = res[1]
    payload += mk_uintvar(width)
    payload += mk_uintvar(height)
    #print(f"header: {payload.hex()}")
    bitmap = [[pixels[x, y] for x in range(img.width)] for y in range(img.height)]

    collection = ""
    cat = 0
    for hline in bitmap:
        for px in hline:
            cat += 1
            if px:
                collection += "1"
            else:
                collection += "0"
            if len(collection) == 8:
                payload += bitstring_to_bytes(collection)
                collection = ""
            if cat == width:
                if collection:
                    while len(collection) < 8:
                        collection += "0"
                    payload += bitstring_to_bytes(collection)
                    collection = ""
                    cat = 0

    return payload

def tonearest8(i: int):
    while not (i%8 == 0):
        i+=1
    return i

def decodewbmp(wbmp: bytes, format: str = 'PNG', returnImageObject: bool = False):
    w = 0
    h = 0
    it = 0

    buffer = bytes()
    headeryeah = False
    bitmap = []
    img = None
    for byte in wbmp:
        if headeryeah:
            for p in range(0, 8):
                bit = (byte >> (7 - p)) & 1
                x = it % w
                y = it // w
                if 0 <= x < w and 0 <= y < h:
                    pixels[x, y] = bit
                it += 1
        else:
            it += 1
            buffer += bytes([byte])
            if it < 3:
                if it == 2:
                    if not buffer == b'\x00\x00':
                        raise Exception("Invalid or unsupported Wbmp!")
                    buffer = b''
            elif w == 0:
                if byte <= 127:  # last byte of uintvar
                    w = decode_uintvar(buffer)
                    buffer = bytearray()
                    oldw = w
                    w = tonearest8(w)
            elif h == 0:
                if byte <= 127:  # last byte of uintvar
                    h = decode_uintvar(buffer)
                    buffer = bytearray()
                    headeryeah = True
                    img = Image.new("1", (w, h))
                    pixels = img.load()
                    it = 0
    ds = w-oldw
    #print(ds)
    img = img.crop((0,0,oldw,h))

    if returnImageObject:
        return img
    else:
        imageData = io.BytesIO()
        img.save(imageData, format=format)
        imageData = imageData.getvalue()
        return imageData

