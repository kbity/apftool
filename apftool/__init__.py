# apftool/__init__.py

from .apftool import encodeapf, decodeapf
from .af2tool import encodeaf2, decodeaf2
from .wbmptool import encodewbmp, decodewbmp
from .otabtool import encodeotab, decodeotab
from .bruhtool import encodebruh, decodebruh

extensions = (".apf", ".apf2", ".aif", ".af2", ".ap2", ".aif2", ".txt", ".text")
extensions_apf = (".apf", ".aif", ".txt", ".text")
extensions_apf2 = (".apf2", ".af2", ".ap2", ".aif2", ".txt")
extensions_wbmp = (".wbmp", ".wbitmap", ".wbm")
extensions_otab = (".otb", ".ota", ".otab")
extensions_bruh = (".bruh", ".brh")

extensions_txt = (".txt", ".text") # txt is seen as a generic container for apf/apf2 because they're just txt files
extensions_all = (".apf", ".apf2", ".aif", ".af2", ".ap2", ".aif2", ".txt", ".text", ".wbmp", ".wbitmap", ".wbm", ".otb", ".ota", ".otab", ".bruh", ".brh") # useful for decodeany

def decodeany(data, format: str = 'PNG', returnImageObject: bool = False):

    if isinstance(data, str):
        return decodeaf2(data, format, returnImageObject) # apf and af2 decoder

    elif isinstance(data, bytes):
        if data.startswith(b'\x00\x00'): # type 00 wbmp header
            return decodewbmp(data, format, returnImageObject)

        elif data.startswith(b'APERTURE IMAGE FORMAT (c) '): # this makes me GLaD
            apfX = data.decode("ascii")
            return decodeaf2(apfX, format, returnImageObject) # yeah ok vrumbler

        # bruh heuristic: everything past the 8th byte should be text
        datapast8th = data[8:]
        bruh = False
        try:
            datapast8th.decode("ascii") # dont even need to keep this just discard it
            bruh = True
        except Exception:
            pass

        if bruh: # looser check that otbs follow
            return decodebruh(data, format, returnImageObject) # assume otb if it doesnt look like a wbmp or doesnt taste like a bruh

        elif data.startswith(b'\x00'): # looser check that otbs follow
            return decodeotab(data, format, returnImageObject) # assume otb if it doesnt look like a wbmp or doesnt taste like a bruh

        else:
            Exception(f"decoding failed! {e}. this likely means the format isnt supported by apftool.")

    else:
        raise Exception("Invalid data! Must be bytes or str")
