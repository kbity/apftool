from PIL import Image
import textwrap, io

def decode(bruh: bytes, format: str = 'PNG', returnImageObject: bool = False):
    # split data from resolution header
    head = bruh[:8]
    body = bruh[8:]

    w = int.from_bytes(head[:4], 'little')
    h = int.from_bytes(head[4:], 'little')

    data = body.decode('ascii')
    lines = data.splitlines()

    img = Image.new("RGB", (w, h))
    pix = img.load()

    for i in range(len(lines)):
        cl = lines[i]
        cll = textwrap.wrap(cl, 6)
        for px in range(len(cll)):
            clll = cll[px]
            pix[px, i] = (int(clll[0:2], 16),int(clll[2:4], 16),int(clll[4:6], 16))

    if returnImageObject:
        return img
    else:
        imageData = io.BytesIO()
        img.save(imageData, format=format)
        imageData = imageData.getvalue()
        return imageData

def encode(img: Image):
    img = img.convert("RGB")
    pixels = img.load()

    bruh = b""
    w, h = img.size
    bruh += w.to_bytes(4, 'little')
    bruh += h.to_bytes(4, 'little')
    brlist = []

    for rw in range(h):
        for p in range(w):
            r, g, b = pixels[p, rw]
            liberal = (f"{r:02X}", f"{g:02X}", f"{b:02X}")
            pix = ''.join(liberal)
            brlist.append(pix)
        brlist.append("\n")
    bstr = "".join(brlist)
    res = bytes(bstr, "ascii")
    bruh += res
    return bruh
