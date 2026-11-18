#!/bin/sh
# End to end: a drawing with an embedded image goes through Edit in GIMP
# (GIMP not launched), which must save the image next to the drawing and
# link it; GIMP (headless, plug-in installed in a throwaway profile)
# paints on it and sends twice, reopening its .xcf in between; Inkscape's
# render of the drawing must then show GIMP's painting.
#
# Copyright 2026 David
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
here=$(cd "$(dirname "$0")" && pwd)
repo=$(dirname "$here")
work=$here/work
gimp_run=${GIMP_RUN:-$repo/../gimp-devtools/gimp-run.sh}
gimp_console=${GIMP_CONSOLE:-$(command -v gimp-console-3.2 || command -v gimp-console-3.0 || command -v gimp-console)}
extensions=${INKSCAPE_EXTENSIONS:-/usr/share/inkscape/extensions}
rm -rf "$work"
mkdir -p "$work/profile/plug-ins"
cp -r "$repo/gimp/inkscape-link" "$work/profile/plug-ins/"

# a drawing with an embedded 64 x 64 green picture (corner transparent)
python3 - "$work" <<'PY'
import base64, io, sys
import numpy as np
from PIL import Image
work = sys.argv[1]
a = np.zeros((64, 64, 4), np.uint8); a[..., 1] = 200; a[..., 3] = 255; a[:8, :8, 3] = 0
buf = io.BytesIO(); Image.fromarray(a).save(buf, "PNG")
uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
open(f"{work}/drawing.svg", "w").write(
    '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
    'width="64" height="64" viewBox="0 0 64 64">'
    f'<image id="pic" width="64" height="64" xlink:href="{uri}"/></svg>')
PY

status=0
DOCUMENT_PATH=$work/drawing.svg PYTHONPATH=$extensions python3 "$repo/inkscape/edit_in_gimp.py" \
    --id=pic --launch=false --output="$work/drawing.svg.new" "$work/drawing.svg"
mv "$work/drawing.svg.new" "$work/drawing.svg"
if grep -q 'xlink:href="drawing_images/pic.png"' "$work/drawing.svg" && [ -f "$work/drawing_images/pic.png" ]; then
    echo "ok   embedded image saved next to the drawing and linked"
else
    echo "FAIL embedded image not extracted and linked"; status=1
fi
cp "$work/drawing_images/pic.png" "$work/picture.png"   # the GIMP test works on picture.png
rm "$work/drawing_images/pic.png"
ln -s ../picture.png "$work/drawing_images/pic.png"

"$gimp_run" --native --home="$work/home" --env=GIMP3_DIRECTORY="$work/profile" \
    --env=TEST_WORK="$work" -- timeout 180 "$gimp_console" --no-interface --no-data --no-fonts \
    --quit --batch-interpreter python-fu-eval -b "exec(open('$here/gimp_send_test.py').read())" \
    > "$work/gimp.log" 2>&1 || true
grep -q "GIMP SEND TEST DONE" "$work/gimp.log" || { echo "FAIL: GIMP did not finish, see $work/gimp.log"; exit 1; }

inkscape "$work/drawing.svg" --export-type=png --export-area-page --export-dpi=96 \
    --export-filename="$work/drawing.png" 2>/dev/null
python3 - "$work" <<'PY' || status=1
import json, sys
import numpy as np
from PIL import Image
work = sys.argv[1]
r = json.load(open(f"{work}/gimp-result.json"))
a = np.asarray(Image.open(f"{work}/drawing.png").convert("RGBA")).astype(int)
checks = [
    ("GIMP sent twice", r["first_send"] and r["second_send"]),
    ("GIMP saved the layers as .xcf", r["xcf_after_first"]),
    ("reopening the .xcf gives the layers back", r["layers_reopened"] == ["red square", "Background"]),
    ("Inkscape shows the red square", (a[20, 20] == [255, 0, 0, 255]).all()),
    ("Inkscape shows the half-transparent blue bar", a[30, 45, 2] > 150 and a[30, 45, 0] < 10),
    ("the hidden GIMP layer is not sent", (a[60, 60] == [0, 200, 0, 255]).all()),
    ("transparency is kept", a[2, 2, 3] == 0),
]
bad = 0
for text, ok in checks:
    print(("ok   " if ok else "FAIL ") + text)
    bad += not ok
print("ALL PASS" if not bad else f"{bad} FAILED")
sys.exit(1 if bad else 0)
PY
exit $status
