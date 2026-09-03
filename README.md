# A library for converting to and from Aperture Science apf files, the custom extended apf2s, otb/wbmp images, and facedev's bruh format.

## basic usage: 

```
import apftool

apfString = apftool.apf.encode(pngObject) # turns image bytes object into apf string
pngObject = apftool.apf.decode(apfString) # turns apf string object into image bytes
```

additional tooling and software using apftool can be found at https://github.com/kbity/apftool, including custom MIME extensions.

## format info:

APF is a custom format made by valve for the Portal 2 ARG. Documentation can be found [here](http://portalwiki.asshatter.org/index.php/Aperture_Image_Format.html).

APF2 is a custom format, and superset of the original Portal 2 ARG Format. Documentation for APF2 can be found [here](https://kbity.github.io/extra/apf2.html).

MQIF is an experimental format from the KQI Hub, designed to demonstrate the usability of the scQOI compression algorithm. Limited info can be found [here](https://kqi-hub.github.io/).

wbmp (Wireless bitmap) and otb (over-the-air bitmap) are simple image formats meant for transfering images before the modern internet was available to cell phones. wbmp came from the WAP forum, and otb came from Nokia. Info can be found [here](https://en.wikipedia.org/wiki/Wireless_Application_Protocol_Bitmap_Format) and [here](https://en.wikipedia.org/wiki/OTA_bitmap) respectively.

bruh is an intentionally terrible format made by facedev. info can be found [here](https://www.youtube.com/watch?v=48B8FPmMT0g)... i guess?

## funcs and features

### encoders:

`apf.encode(img: bytes | Image.Image, lineskip: int = 1, findbestlineskip: bool = False, returnbytes: bool = False)` takes image bytes or pil image object and outputs apf string. lineskip is interleave value, findbestlineskip brute-forces different interleave values to the possible max of 199 and uses the smallest one. returnbytes makes it return bytes instead of a string.

`apf2.encode(img: bytes | Image.Image, lineskip: int = 1, findbestlineskip: bool = False, legacy: bool = False, trans = False, pal: int = 95, desc: str = "", prepalette: str = None, dodithering: bool = False, returnbytes: bool = False)` takes image bytes or pil image object and outputs af2 string. lineskip is interleave value, findbestlineskip brute-forces different interleave values to the provided lineskip and uses the smallest one. legacy uses apf1-style 2 color data instead of a 95 color palette. trans sets transparency mode, with mode 0 being off, mode 1 being index 0 transparency (GIF-like, it overrides a color), and mode 2 being indexed alpha. pal allows you to manually force a smaller or larger palette anything over 95 will use APF2-1994's Dual Indexed Mode. Prepalette is an already encoded APF2 palette you input into the encoder to make the colors deterministic. dodithering enables or disables dithering. returnbytes makes it return bytes instead of a string.

`wbmp.encode(img: Image)` takes pil image object and outputs wbmp bytes

`otb.encode(img: Image, width=255, height=255)` takes pil image object and outputs otb bytes. max size is 255x255. the size input is max size, the output may be smaller

`bruh.encode(img: Image)` takes pil image object and outputs bruh bytes

`mqif.encode(img: list | Image.Image, transcolor: tuple = None)` 

### decoders:

`decode(data, format: str = 'PNG', returnImageObject: bool = False)` takes in string or bytes and outputs bytes image or PIL image using best-guess for the decoders

`apf.decode(apf: str, format: str = 'PNG', returnImageObject: bool = False)` takes apf string and outputs either image bytes in specified format or pil image object

`apf2.decode(af2: str, format: str = 'PNG', returnImageObject: bool = False, provide_extra_data: bool = False)` Literally a dropin replacement for decodeapf. provide_extra_data outputs frame delay data if applicable

`wbmp.decode(wbmp: bytes, format: str = 'PNG', returnImageObject: bool = False)` takes wbmp bytes and outputs either image bytes in specified format or pil image object

`otb.decode(otab: bytes, format: str = 'PNG', returnImageObject: bool = False)` hi i have the same usage as decodewbmp but for .otb images

`bruh.decode(bruh: bytes, format: str = 'PNG', returnImageObject: bool = False)` bruh decoder, acts the same as the others.

`mqif.decode(mqif: bytes, format: str = 'GIF', returnImageObject: bool = False, provide_extra_data: bool = False)` mqif decoder, acts the same as the others but defaults to GIF to support animation. provide_extra_data outputs frame delay data if applicable.

### misc:

apftool provides many extensions tuples:

`extensions` - apf/apf2 extensions

`extensions_apf` - apf extensions

`extensions_apf2` - apf2 extensions

`extensions_wbmp` - wbmp extensions

`extensions_otb` - otb extensions

`extensions_bruh` - bruh extensions

`extensions_mqif` - mqif extensions

`extensions_txt` - txt extensions, useful for weeding out generic apf

`extensions_all` - all supported apftool extensions, useful for universal decoder

## dependancies

`PIL (pillow)` is required

`numpy` and `scikit-learn` are needed for high-speed APF2-1994 257+ Color Encoding, if missing the code will use a very slow fallback.

## changelog:

1.0.0 - restructure ABI, add MQIF support. Legacy ABI will be emulated. Also improve bruh and apf encoding speed. Also make apf2 decoder force webp for animated images in dual-indexed mode.

0.5.16 - add apfcli to the main project, fix dithering, fix palette edge cases, and rename encodeaf2 and decodeaf2 to encodeapf2 and decodeapf2

0.5.15 - add option to toggle dithering to the apf2 encoder and decoder

0.5.14 - update apf/apf2 encoder and decoder to use union types

0.5.13 - make the fixed palette thing not use a stupid amount of memory by using sklearn

0.5.12 - fix encoder with bytes input comparing against literal "bytes" type

0.5.11 - fix encoder trying to decode a non-existant input palette

0.5.10 - add predefined palette input for encoding, and remove duplicated code in the decode data functions

0.5.9 - fix wbmp encoding

0.5.8 - improve encoding speed for apf2 and wbmp

0.5.7 - fix index 0 bug with transparency mode 2 in 9025 color mode

0.5.6 - damn it i left the file testing code in af2tool

0.5.5 - implement apf2-1994 encoding and decoding (broken release)

0.5.2 - add bruh heristic to decodeany

0.5.1 - attempt to fix bruh resolution parsing issue

0.5.0 - add bruh encoder and decoder

0.4.3 - actually improve otb quality

0.4.2 - did not improve otb quality

0.4.1 - improve readme.md, fix otb encoder skuing due to flushing

0.4.0 - add support for otb images, improve readme.md, and add decodeany to decode all suported formats automatically

0.3.3 - make the af2 decoder more lenient

0.3.2 - i forgot but i think it made the af2 decoder more lenient

0.3.1 - fix 0.3.0

0.3.0 - add support for wbmp images, broken release

0.2.x - add apf2 support, i dont remember all the changes of the 0.2.x line

0.10 - initial release
