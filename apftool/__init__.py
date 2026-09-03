# apftool/__init__.py

from . import bruh, otb, wbmp, apf, apf2, mqif, scqoi, bittools
from .apfcli import main as cli

extensions = (".apf", ".apf2", ".aif", ".af2", ".ap2", ".aif2")
extensions_apf = (".apf", ".aif")
extensions_apf2 = (".apf2", ".af2", ".ap2", ".aif2")
extensions_wbmp = (".wbmp", ".wbitmap", ".wbm")
extensions_otb = (".otb", ".ota", ".otab")
extensions_bruh = (".bruh", ".brh")
extensions_mqif = (".mqif", ".mqi")

extensions_txt = (".txt", ".text") # txt is seen as a generic container for apf/apf2 because they're just txt files

extensions_all = []
extensions_all.extend(extensions_apf+extensions_apf2+extensions_wbmp+extensions_otb+extensions_bruh+extensions_mqif)

def decode(data, format: str = None, returnImageObject: bool = False, provide_extra_data=True):
    if isinstance(data, str):
        if format is None:
            format = "PNG"
        return apf2.decode(data, format, returnImageObject) # apf and af2 decoder

    elif isinstance(data, bytes):
        if data.startswith(b'APERTURE IMAGE FORMAT (c) '): # this makes me GLaD
            if format is None:
                format = "PNG"
            return apf2.decode(data, format, returnImageObject, provide_extra_data=provide_extra_data)

        elif data.startswith(b'QIF26a'): # mqif header
            if format is None:
                format = "WebP"
            return mqif.decode(data, format, returnImageObject, provide_extra_data=provide_extra_data) # discard the frame timing data not functional in this API. speaking of that I should make APF2 provide that

        elif data.startswith(b'\x00\x00'): # type 00 wbmp header
            if format is None:
                format = "PNG"
            return wbmp.decode(data, format, returnImageObject)

        # bruh heuristic: everything past the 8th byte should be text
        datapast8th = data[8:]
        isbruh = False
        try:
            datapast8th.decode("ascii") # dont even need to keep this just discard it
            isbruh = True
        except Exception:
            pass

        if isbruh: # looser check that otbs follow
            if format is None:
                format = "PNG"
            return bruh.decode(data, format, returnImageObject) # assume otb if it doesnt look like a wbmp or doesnt taste like a bruh

        elif data.startswith(b'\x00'): # looser check that otbs follow
            if format is None:
                format = "PNG"
            return otb.decode(data, format, returnImageObject) # assume otb if it doesnt look like a wbmp or doesnt taste like a bruh

        else:
            Exception(f"decoding failed! {e}. this likely means the format isnt supported by apftool.")

    else:
        raise Exception("Invalid data! Must be bytes or str")

#compatabiliy shims
extensions_otab = extensions_otb
decodeaf2 = apf2.decode
encodeaf2 = apf2.encode
decodeapf2 = apf2.decode
encodeapf2 = apf2.encode
decodeapf = apf.decode
encodeapf = apf.encode
decodewbmp = wbmp.decode
encodewbmp = wbmp.encode
decodeotab = otb.decode
encodeotab = otb.encode
decodebruh = bruh.decode
encodebruh = bruh.encode
decodeany = decode
