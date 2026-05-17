apf2web is a Pillow-less port of apftool's af2decode function (APF2toPPM) but with the PPM replaced by a JavaScript Canvas.

Usage:
* you must add `<script type="module" src="https://pyscript.net/releases/2024.1.1/core.js"></script>` to the top of the document
* `<script src="/path/to/apf2web.py" type="py"></script>` has to be near the bottom of the document, or after all APF2
* to load an APF2, you just do `<canvas data-apf2web-src="/path/to/file.apf2"></canvas>`
