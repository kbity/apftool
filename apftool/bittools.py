def byte_to_boollist(byte: int):
    lis = []
    for n in [128, 64, 32, 16, 8, 4, 2, 1]:
        if byte >= n:
            byte -= n
            lis.append(True)
        else:
            lis.append(False)
    return lis

def boollist_to_int_var(boollist: list):
    h = 2**(len(boollist)-1)
    itnegr = 0
    for bolin in boollist:
        if bolin:
            itnegr += h
        h = h >> 1
    return itnegr

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

def generate_boollist(dat: int, ln: int):
    boollist = []
    for i in reversed(range(ln)):
        x = 1 << i
        if dat >= x:
            dat -= x
            boollist.append(True)
        else:
            boollist.append(False)
    return boollist

def intclamp(inpt):
    return int(inpt) % 256
