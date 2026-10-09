from .bittools import byte_to_boollist, boollist_to_int_var

def compress(inpt: bytes):
    buffr = []
    output = bytearray()
    for byte in inpt:
        buffr.extend(byte_to_boollist(byte)[1:])
        if len(buffr) >= 8:
            output.append(boollist_to_int_var(buffr[0:8]))
            buffr = buffr[8:]
    if buffr:
        while len(buffr) < 8:
            buffr.append(False)
        output.append(boollist_to_int_var(buffr))
    return output

def decompress(inpt: bytes):
    buffr = []
    output = bytearray()
    for byte in inpt:
        buffr.extend(byte_to_boollist(byte))
        while len(buffr) >= 8:
            v = boollist_to_int_var([0]+buffr[0:7])
            if v:
                output.append(v)
            buffr = buffr[7:]
    return output
