# Copyright 2026 David
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Run inside GIMP 3 (python-fu-eval) with the plug-in installed and
# TEST_WORK set: opens $TEST_WORK/picture.png as Inkscape's Edit in GIMP
# would, paints on a new layer, sends; then reopens the .xcf it saved,
# adds a layer, sends again. Writes $TEST_WORK/gimp-result.json.
import json
import os

from gi.repository import Gegl, Gimp, Gio

W = os.environ["TEST_WORK"]
picture = os.path.join(W, "picture.png")
pdb = Gimp.get_pdb()
result = {}


def run_send(image):
    proc = pdb.lookup_procedure("plug-in-inkscape-link-send")
    config = proc.create_config()
    config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    config.set_property("image", image)
    out = proc.run(config)
    return out.index(0) == Gimp.PDBStatusType.SUCCESS


def paint(image, name, x, y, w, h, rgba):
    layer = Gimp.Layer.new(
        image, name, w, h, Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL
    )
    image.insert_layer(layer, None, 0)
    layer.set_offsets(x, y)
    buf = layer.get_buffer()
    buf.set(Gegl.Rectangle.new(0, 0, w, h), "R'G'B'A u8", bytes(rgba) * (w * h))
    buf.flush()


image = Gimp.file_load(Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(picture))
paint(image, "red square", 10, 10, 20, 20, (255, 0, 0, 255))
result["first_send"] = run_send(image)
result["xcf_after_first"] = os.path.isfile(picture + ".xcf")
image.delete()

image = Gimp.file_load(
    Gimp.RunMode.NONINTERACTIVE, Gio.File.new_for_path(picture + ".xcf")
)
result["layers_reopened"] = [layer.get_name() for layer in image.get_layers()]
paint(image, "blue bar", 40, 5, 10, 50, (0, 0, 255, 128))
hidden = Gimp.Layer.new(
    image, "hidden", 64, 64, Gimp.ImageType.RGBA_IMAGE, 100, Gimp.LayerMode.NORMAL
)
image.insert_layer(hidden, None, 0)
hidden.fill(Gimp.FillType.FOREGROUND)
hidden.set_visible(False)
result["second_send"] = run_send(image)
image.delete()
with open(os.path.join(W, "gimp-result.json"), "w") as f:
    json.dump(result, f)
print("GIMP SEND TEST DONE")
