from .bittools import byte_to_boollist, boollist_to_int_var
windowsize = 64

# scQOI Thing
def compress(originaldata):
    compresseddata = bytearray()
    cache = []
    runlen = 0
    prevbyte = None
    for _ in range(windowsize):
        cache.append(None)
    for byte in originaldata:
        if byte == prevbyte:
            runlen += 1
            if runlen >= 63:
                compresseddata.append(runlen)
                runlen = 0
        else:
            if runlen:
                compresseddata.append(runlen)
            runlen = 0
            if byte in cache:
                compresseddata.append(128+(63-cache.index(byte)))
            else:
                cache.append(byte)
                del cache[0]
                if prevbyte is not None:
                    diff = (byte - prevbyte) % 256
                    if diff > 127:
                        diff -= 256
                else:
                    diff = 255
                if (diff <= 31) and (diff >= -32):
                    if diff < 0:
                        diff+=64
                    compresseddata.append(64+diff)
                else:
                    compresseddata.append(255)
                    compresseddata.append(byte)
        prevbyte = byte
    if runlen: # flush run
        compresseddata.append(runlen)
    return bytes(compresseddata)

def decompress(compresseddata):
    originaldata = bytearray()
    cache = []
    runlen = 0
    skip = False
    for _ in range(windowsize):
        cache.append(None)
    for byte in compresseddata:
        if skip:
            skip = False
            originaldata.append(byte)
            cache.append(byte)
            del cache[0]
            continue
        else:
            bl = byte_to_boollist(byte)
            bytetype = boollist_to_int_var(bl[0:2])
            bytedata = boollist_to_int_var(bl[2:8])
            if bytetype == 3: # SCQ_OP_BYTE
                skip = True
            elif bytetype == 2: # SCQ_OP_INDEX
                originaldata.append(cache[63-bytedata])
            elif bytetype == 1: # SCQ_OP_DIFF
                if bytedata > 31:
                    bytedata -= 64
                bt = (originaldata[-1]+bytedata) % 256
                try:
                    originaldata.append(bt)
                except Exception as e:
                    print(originaldata[-1])
                    print(bytedata)
                    raise e
                cache.append(originaldata[-1])
                del cache[0]
            elif bytetype == 0: # SCQ_OP_RUN
                for _ in range(bytedata):
                    originaldata.append(originaldata[-1])

    return bytes(originaldata)
