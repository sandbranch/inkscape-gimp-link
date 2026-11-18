#!/usr/bin/env python3
# Copyright (C) 2026 David
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
"""
GIMP 3 plug-in: File > Inkscape Link > Send to Inkscape.

Writes the visible image (layers merged, transparency kept) back to the
image file Inkscape links to, and saves the layers next to it as
<image>.xcf, which Inkscape's Edit in GIMP opens next time. Inkscape
reloads the image by itself.

Which file: for an image opened from <file>.xcf, <file> (the .xcf name
without its ending); for an image opened from the picture itself, that
file.
"""

import os
import sys

import gi

gi.require_version("Gimp", "3.0")
from gi.repository import Gimp, Gio, GLib

SEND = "plug-in-inkscape-link-send"
MENU = "<Image>/File/Inkscape Link"


class LinkError(Exception):
    pass


def target_of(image):
    """(picture file, xcf file) for this image."""
    xcf = image.get_xcf_file()
    if xcf is not None and xcf.get_path():
        path = xcf.get_path()
        if path.lower().endswith(".xcf") and os.path.splitext(path[:-4])[1]:
            return path[:-4], path
    picture = image.get_imported_file() or image.get_file()
    if picture is None or not picture.get_path():
        raise LinkError(
            "this image did not come from Inkscape (open it with Edit in GIMP)"
        )
    path = picture.get_path()
    if path.lower().endswith(".xcf"):
        raise LinkError(
            f"cannot tell which picture {os.path.basename(path)} belongs to"
        )
    return path, path + ".xcf"


def flattened(image):
    """A copy with the visible layers merged, image-sized, with alpha."""
    dup = image.duplicate()
    dup.undo_disable()
    for layer in dup.get_layers():
        if not layer.get_visible():
            dup.remove_layer(layer)
    layers = dup.get_layers()
    if not layers:
        dup.delete()
        raise LinkError("nothing visible to send")
    merged = (
        layers[0]
        if len(layers) == 1
        else dup.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
    )
    if (merged.get_width(), merged.get_height()) != (
        dup.get_width(),
        dup.get_height(),
    ) or tuple(merged.get_offsets()[1:]) != (0, 0):
        merged.resize_to_image_size()
    return dup


def send(image):
    picture, xcf = target_of(image)
    folder = os.path.dirname(picture)
    base, ext = os.path.splitext(os.path.basename(picture))
    tmp = os.path.join(folder, f".{base}.{os.getpid()}.tmp{ext}")
    dup = flattened(image)
    try:
        if not Gimp.file_save(
            Gimp.RunMode.NONINTERACTIVE, dup, Gio.File.new_for_path(tmp), None
        ):
            raise LinkError(f"GIMP could not write {tmp}")
        os.replace(tmp, picture)  # whole file at once: Inkscape never reads half of it
    finally:
        dup.delete()
        if os.path.exists(tmp):
            os.unlink(tmp)
    if not Gimp.file_save(
        Gimp.RunMode.NONINTERACTIVE, image, Gio.File.new_for_path(xcf), None
    ):
        raise LinkError(f"could not save {xcf}")
    image.clean_all()
    return picture, xcf


class InkscapeLink(Gimp.PlugIn):
    def do_query_procedures(self):
        return [SEND]

    def do_set_i18n(self, name):
        return False

    def do_create_procedure(self, name):
        if name != SEND:
            return None
        p = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, self.run_send, None
        )
        p.set_image_types("*")
        p.set_menu_label("_Send to Inkscape")
        p.add_menu_path(MENU)
        p.set_sensitivity_mask(
            Gimp.ProcedureSensitivityMask.DRAWABLE
            | Gimp.ProcedureSensitivityMask.DRAWABLES
            | Gimp.ProcedureSensitivityMask.NO_DRAWABLES
        )
        p.set_documentation(
            "Send the image back to Inkscape",
            "Writes the visible image to the picture Inkscape links to and saves the "
            "layers as <picture>.xcf next to it. Inkscape reloads the picture.",
            name,
        )
        p.set_attribution("David", "David", "2026")
        return p

    def run_send(self, procedure, run_mode, image, drawables, config, data):
        try:
            send(image)
        except (LinkError, OSError, GLib.Error) as error:
            if run_mode == Gimp.RunMode.INTERACTIVE:
                Gimp.message(f"Send to Inkscape: {error}")
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR,
                GLib.Error.new_literal(
                    GLib.quark_from_string("inkscape-link"), str(error), 0
                ),
            )
        # no message on success: sending is done often, Inkscape shows the result
        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


Gimp.main(InkscapeLink.__gtype__, sys.argv)
