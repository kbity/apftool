// apf2web.js - translated from pyscript by ChatGPT

const af2headertext = "APERTURE IMAGE FORMAT (c) 1993";
const af2headertext1994 = "APERTURE IMAGE FORMAT (c) 1994";

function chunkString(str, size) {
    const out = [];
    for (let i = 0; i < str.length; i += size) {
        out.push(str.slice(i, i + size));
    }
    return out;
}

function af2_apfdecodedata(data, h, w, lineskip, pals, trans = false) {
    const apfbuffer = Array.from({ length: h }, () =>
        Array.from({ length: w }, () => null)
    );

    let x = 0;
    let y = h - 1;
    let passoffset = 0;
    let state = false;

    for (const char of data) {
        const runlen = char.charCodeAt(0) - 32;

        for (let i = 0; i < runlen; i++) {
            if (y >= 0 && y < h && x >= 0 && x < w) {
                apfbuffer[y][x] = state ? pals[1] : pals[0];
            }

            x++;

            if (!(x < w)) {
                y -= lineskip;
                x = 0;
            }

            if (y < 0) {
                y = h - 1;
                passoffset++;
                y -= passoffset;
            }
        }

        state = !state;
    }

    return apfbuffer;
}

function af2decodedata(data, h, w, lineskip, pals, trans = 0) {
    const apfbuffer = Array.from({ length: h }, () =>
        Array.from({ length: w }, () => null)
    );

    let x = 0;
    let y = h - 1;
    let passoffset = 0;

    let segsize = trans === 2 ? 9 : 7;

    const palsegments = chunkString(pals, segsize);
    const pal = {};

    for (const col of palsegments) {
        const ind = col[0];
        const hexcs = col.slice(1);
        const hexcsegment = chunkString(hexcs, 2);

        if (trans === 2) {
            pal[ind] = [
                parseInt(hexcsegment[0], 16),
                parseInt(hexcsegment[1], 16),
                parseInt(hexcsegment[2], 16),
                parseInt(hexcsegment[3], 16)
            ];
        } else {
            pal[ind] = [
                parseInt(hexcsegment[0], 16),
                parseInt(hexcsegment[1], 16),
                parseInt(hexcsegment[2], 16)
            ];
        }
    }

    if (trans === 1) {
        pal[" "] = [0, 0, 0, 0];
    }

    for (let pair = 0; pair < Math.floor(data.length / 2); pair++) {
        const color = data[pair * 2];
        const runlen = data.charCodeAt(pair * 2 + 1) - 32;

        for (let i = 0; i < runlen; i++) {
            if (y >= 0 && y < h && x >= 0 && x < w) {
                apfbuffer[y][x] = pal[color];
            }

            x++;

            if (x >= w) {
                y -= lineskip;
                x = 0;
            }

            if (y < 0) {
                y = h - 1;
                passoffset++;
                y -= passoffset;
            }
        }
    }

    return apfbuffer;
}

function af2_1994_decodedata(data, h, w, lineskip, pals, trans = 0) {
    const apfbuffer = Array.from({ length: h }, () =>
        Array.from({ length: w }, () => null)
    );

    let x = 0;
    let y = h - 1;
    let passoffset = 0;

    let segsize = trans === 2 ? 10 : 8;

    const palsegments = chunkString(pals, segsize);
    const pal = {};

    for (const col of palsegments) {
        const ind = col.slice(0, 2);
        const hexcs = col.slice(2);
        const hexcsegment = chunkString(hexcs, 2);

        if (trans === 2) {
            pal[ind] = [
                parseInt(hexcsegment[0], 16),
                parseInt(hexcsegment[1], 16),
                parseInt(hexcsegment[2], 16),
                parseInt(hexcsegment[3], 16)
            ];
        } else {
            pal[ind] = [
                parseInt(hexcsegment[0], 16),
                parseInt(hexcsegment[1], 16),
                parseInt(hexcsegment[2], 16)
            ];
        }
    }

    if (trans === 2) {
        pal["  "] = [0, 0, 0, 0];
    }

    for (let pair = 0; pair < Math.floor(data.length / 3); pair++) {
        const color =
            data[pair * 3] +
            data[pair * 3 + 1];

        const runlen =
            data.charCodeAt(pair * 3 + 2) - 32;

        for (let i = 0; i < runlen; i++) {
            if (y >= 0 && y < h && x >= 0 && x < w) {
                apfbuffer[y][x] = pal[color];
            }

            x++;

            if (x >= w) {
                y -= lineskip;
                x = 0;
            }

            if (y < 0) {
                y = h - 1;
                passoffset++;
                y -= passoffset;
            }
        }
    }

    return apfbuffer;
}

function decodeaf2(
    af2,
    format = null,
    returnImageObject = false,
    returnFrames = false
) {
    if (![null, "PPM", "PAM"].includes(format)) {
        throw new Error("Unsupported Format!");
    }

    let apf_list = af2.split(/\r?\n/);
    let apf_lines = apf_list.filter(line => line);

    if (apf_lines[0].trim() === "APERTURE IMAGE FORMAT (c) 1985") {
        af2 =
            `APERTURE IMAGE FORMAT (c) 1993\n320x200,l,${apf_list[1]}\n.\n${apf_list[2]}`;

        apf_lines = af2.split(/\r?\n/);
    }

    const header = apf_lines[0].trim();

    if (
        header !== af2headertext &&
        header !== af2headertext1994
    ) {
        throw new Error("Invalid Aperture Image Format File");
    }

    const metadata = apf_lines[1].trim().split(",");

    const delay = metadata.length > 4
        ? parseInt(metadata[4])
        : 100;

    const [w, h] = metadata[0]
        .split("x")
        .map(v => parseInt(v));

    const argumentsField = metadata[1];
    const lineskip = parseInt(metadata[2]);

    let mode;

    if (argumentsField.includes("l")) {
        mode = "legacy";
    } else if (argumentsField.includes("d")) {
        mode = "apf2-1994";
    } else {
        mode = "apf2";
    }

    let datatype;
    let data;

    if (argumentsField.includes("m")) {
        datatype = "multistream";
        data = apf_lines.slice(3);
    } else {
        datatype = "singlestream";
        data = apf_lines[3];
    }

    let istrans = Number(argumentsField.includes("t"));

    if (!istrans) {
        istrans = Number(argumentsField.includes("a")) * 2;
    }

    if (format === null) {
        format = istrans ? "PAM" : "PPM";
    }

    const imgs = [];

    function decodeFrame(ds, pals) {
        if (mode === "legacy") {
            return af2_apfdecodedata(
                ds,
                h,
                w,
                lineskip,
                pals,
                istrans
            );
        }

        if (mode === "apf2-1994") {
            return af2_1994_decodedata(
                ds,
                h,
                w,
                lineskip,
                pals,
                istrans
            );
        }

        return af2decodedata(
            ds,
            h,
            w,
            lineskip,
            pals,
            istrans
        );
    }

    let pals = apf_lines[2];

    if (mode === "legacy") {
        pals = pals.split(".");

        function parseLegacyColor(c, fallback) {
            if (c === "") return fallback;

            const seg = chunkString(c, 2);

            return [
                parseInt(seg[0], 16),
                parseInt(seg[1], 16),
                parseInt(seg[2], 16)
            ];
        }

        pals[0] = parseLegacyColor(
            pals[0],
            istrans === 1
                ? [0, 0, 0, 0]
                : [0, 0, 0]
        );

        pals[1] = parseLegacyColor(
            pals[1],
            [255, 255, 255]
        );
    }

    if (datatype === "multistream") {
        for (const ds of data) {
            imgs.push(decodeFrame(ds, pals));
        }
    } else {
        imgs.push(decodeFrame(data, pals));
    }

    if (returnFrames) {
        return imgs;
    }

    return imgs[0];
}

function bitmap_to_imagedata(bitmap) {
    const h = bitmap.length;
    const w = bitmap[0].length;

    const buf = new Uint8ClampedArray(w * h * 4);

    let i = 0;

    for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
            const px = bitmap[y][x];

            buf[i] = px[0];
            buf[i + 1] = px[1];
            buf[i + 2] = px[2];
            buf[i + 3] = px.length > 3 ? px[3] : 255;

            i += 4;
        }
    }

    return new ImageData(buf, w, h);
}

async function load_canvas_from_attr() {
    const canvases = document.querySelectorAll(
        "canvas[data-apf2web-src]"
    );

    for (const canvas of canvases) {
        const src = canvas.getAttribute(
            "data-apf2web-src"
        );

        const resp = await fetch(src);
        const text = await resp.text();

        const bitmap = decodeaf2(
            text,
            null,
            true,
            true
        )[0];

        const img = bitmap_to_imagedata(bitmap);

        canvas.width = img.width;
        canvas.height = img.height;

        const ctx = canvas.getContext("2d");
        ctx.putImageData(img, 0, 0);
    }
}

load_canvas_from_attr();
