# A library for converting to and from Aperture Science apf files, the custom extended apf2s, and otb/wbmp images.

## usage: 

```
import apftool

apfString = apftool.encodeapf(pngObject) # turns image bytes object into apf string
pngObject = apftool.decodeapf(apfString) # turns apf string object into image bytes
```

## funcs and features

### encoders:

`encodeapf(img: bytes, lineskip: int = 1, findbestlineskip: bool = False)` takes image bytes and outputs apf string. lineskip is interleave value, findbestlineskip brute-forces different interleave values to the possible max of 199 and uses the smallest one.

`encodeaf2(img: bytes, lineskip: int = 1, findbestlineskip: bool = False, legacy: bool = False, trans: bool = False, pal: int = 95)` takes image bytes and outputs af2 string. lineskip is interleave value, findbestlineskip brute-forces different interleave values to the provided lineskip and uses the smallest one. legacy uses apf1-style 1 color data instead of a 95 color palette. trans enables/disables transparency, which overrides a color. pal allows you to manually force a smaller palette.

`encodewbmp(img: Image)` takes pil image object and outputs wbmp bytes

`encodeotab(img: Image, width=255, height=255)` takes pil image object and outputs otb bytes. max size is 255x255

### decoders:

`decodeany(data, format: str = 'PNG', returnImageObject: bool = False)` takes in string or bytes and outputs bytes image or PIL image using best-guess for the decoders

`decodeapf(apf: str, format: str = 'PNG', returnImageObject: bool = False)` takes apf string and outputs either image bytes in specified format or pil image object

`decodeaf2(af2: str, format: str = 'PNG', returnImageObject: bool = False)` hi i am the same thing, i am literally a dropin replacement for decodeapf too

`decodewbmp(wbmp: bytes, format: str = 'PNG', returnImageObject: bool = False)` takes wbmp bytes and outputs either image bytes in specified format or pil image object

`decodeotab(otab: bytes, format: str = 'PNG', returnImageObject: bool = False)` hi i have the same usage as decodewbmp but for .otb images

### misc:

apftool provides many extensions tuples:

`extensions` - apf/apf2 extensions

`extensions_apf` - apf extensions

`extensions_apf2` - apf2 extensions

`extensions_wbmp` - wbmp extensions

`extensions_otab` - otb extensions

`extensions_txt` - txt extensions, useful for weeding out generic apf

`extensions_all` - all supported apftool extensions, useful for decodeany

## dependancies

`PIL, io, textwrap, math` (apftool)

most of these a builtins but you may need to install PIL seperately

## changelog:

0.4.3 - actually improve otb quality

0.4.2 - did not improve otb quality

0.4.1 - improve readme.md, fix otb encoder skuing due to flushing

0.4.0 - add support for otb images, improve readme.md, and add decodeany to decode all suported formats automatically

0.3.3 - make the af2 decoder more lenient

0.3.2 - i forgot but i think it made the af2 decoder more lenient

0.3.1 - fix 0.3.0

0.3.0 - add support for wbmp images, broken release