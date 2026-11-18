# Inkscape ↔ GIMP: edit images in GIMP, keep the layers

In Inkscape, select an image and choose **Extensions > Images > Edit in
GIMP**. Paint and add layers in GIMP, then **File > Inkscape Link > Send
to Inkscape**: the image in your drawing updates by itself, and your GIMP
layers are kept for the next edit.

What Inkscape's own "Edit Externally..." does not do:

- **Embedded images too.** An embedded image is saved next to the drawing
  (in a folder named `<drawing>_images`) and linked, so GIMP can write it
  back. (Inkscape offers "Edit Externally" only for linked images.)
- **Your layers stay.** Send writes the visible picture (layers merged,
  transparency kept, hidden layers left out) to the image file, and saves
  the layers as `<image>.xcf` next to it. Next time, Edit in GIMP opens
  that `.xcf`, with all your layers, instead of the flat picture.
- If the picture changed after GIMP last saved its layers (edited in
  another program), Edit in GIMP says so; File > Open as Layers in GIMP
  brings the newer picture in.

Inkscape shows the change when the file changes on disk, through its own
setting **Preferences > Imported Images > Automatically reload images**
(on by default).

The picture is written to a temporary file first and then moved into
place, so Inkscape never reads a half-written file.

## Install

    dev/install.sh            # symlinks; then restart Inkscape and GIMP
    dev/install.sh --uninstall

Or copy `inkscape/edit_in_gimp.inx` and `.py` into Inkscape's extensions
folder, and the folder `gimp/inkscape-link/` into GIMP 3's `plug-ins`
folder (keep `inkscape-link.py` executable). Tip: in GIMP, Edit >
Keyboard Shortcuts, search "Send to Inkscape", give it a key.

Needs GIMP 3 with Python (the Ubuntu `gimp` package has it) and Inkscape
1.2 or later. Tested with Inkscape 1.4.3 and GIMP 3.2.8 on Ubuntu, both
native packages. For a GIMP Flatpak, set the GIMP program in the
extension's dialog to `flatpak run org.gimp.GIMP` (not tested).

## Tests

- `tests/run.sh`: a drawing with an embedded image goes through Edit in
  GIMP (without starting GIMP) and must come out linked to a saved copy;
  GIMP, headless with the plug-in in a throwaway profile, paints on it,
  sends, reopens its `.xcf`, adds a half-transparent layer and a hidden
  one, sends again; Inkscape's render of the drawing must show exactly
  that. Needs `gimp-console-3.x` and
  [gimp-devtools](https://github.com/sandbranch/gimp-devtools)' `gimp-run.sh`
  next to this repo.
- `tests/test_edit_in_gimp.py`: the Inkscape side alone (inkex needed).

Inkscape's automatic reload itself happens in its window, so it is not
part of the tests.

## Licence

GPL-3.0-or-later, see `COPYING`.
