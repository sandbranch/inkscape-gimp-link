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
Edit an image of the drawing in GIMP, keeping GIMP's layers between
edits.

An embedded image is first saved as a PNG next to the drawing and
linked, so that GIMP can write it back. GIMP opens <image>.xcf when there
is one (the layers of the last edit), else the image itself. In GIMP,
File > Inkscape Link > Send to Inkscape writes the image back and saves
the layers as <image>.xcf; Inkscape reloads linked images that change
on disk (Preferences > Imported Images > Automatically reload images).
"""

import base64
import os
import re
import shutil
import subprocess
from urllib.parse import unquote, urlparse

import inkex
from inkex.localization import inkex_gettext as _

EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/tiff": ".tif",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}


def linked_path(image, folder):
    href = image.get("xlink:href") or image.get("href") or ""
    if not href or href.startswith("data:"):
        return None
    path = unquote(urlparse(href).path) if href.startswith("file:") else href
    if not os.path.isabs(path) and folder:
        path = os.path.join(folder, path)
    return os.path.normpath(path)


class EditInGimp(inkex.EffectExtension):
    """Open the selected image in GIMP; GIMP sends it back"""

    def add_arguments(self, pars):
        pars.add_argument("--tab")
        pars.add_argument(
            "--gimp", default="", help="GIMP program; empty: Inkscape's bitmap editor"
        )
        pars.add_argument(
            "--launch",
            type=inkex.Boolean,
            default=True,
            help="false: only prepare (tests)",
        )

    def editor(self):
        if self.options.gimp.strip():
            return self.options.gimp.strip()
        return "gimp"

    def extract(self, image, folder):
        """Save an embedded image next to the drawing and link it there."""
        href = image.get("xlink:href") or image.get("href")
        match = re.match(r"data:([^;,]+)?(;base64)?,(.*)", href, re.DOTALL)
        if not match:
            raise inkex.AbortExtension(_("This image's data could not be read."))
        mime, is_b64, payload = match.groups()
        data = (
            base64.b64decode(re.sub(r"\s+", "", payload))
            if is_b64
            else unquote(payload).encode("latin-1")
        )
        doc = os.path.splitext(os.path.basename(self.document_path() or "drawing"))[0]
        subfolder = f"{doc}_images"
        os.makedirs(os.path.join(folder, subfolder), exist_ok=True)
        stem = image.get("id") or "image"
        name = os.path.join(subfolder, stem + EXTENSIONS.get(mime or "", ".png"))
        target = os.path.join(folder, name)
        with open(target, "wb") as f:
            f.write(data)
        image.set("xlink:href", name.replace(os.sep, "/"))
        if image.get("href"):
            image.set("href", None)
        return target

    def effect(self):
        images = list(self.svg.selection.filter(inkex.Image).values())
        if not images:
            raise inkex.AbortExtension(_("Select an image to edit in GIMP."))
        if len(images) > 1:
            raise inkex.AbortExtension(_("Select one image."))
        image = images[0]
        folder = self.svg_path()
        target = linked_path(image, folder)
        if target is None:
            if not folder:
                raise inkex.AbortExtension(
                    _(
                        "Save the drawing first: the image is stored next to it for GIMP."
                    )
                )
            target = self.extract(image, folder)
        elif not os.path.isfile(target):
            raise inkex.AbortExtension(
                _("The linked image is missing: {}").format(target)
            )
        layered = target + ".xcf"
        to_open = layered if os.path.isfile(layered) else target
        if (
            os.path.isfile(layered)
            and os.path.getmtime(target) > os.path.getmtime(layered) + 1
        ):
            inkex.errormsg(
                _(
                    "The image changed after GIMP last saved its layers ({}). GIMP opens "
                    "the layers; File > Open as Layers brings in the newer image."
                ).format(os.path.basename(layered))
            )
        if self.options.launch:
            program = self.editor()
            if not shutil.which(program.split()[0]):
                raise inkex.AbortExtension(
                    _("GIMP was not found ({}).").format(program)
                )
            subprocess.Popen(
                [*program.split(), to_open],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )


if __name__ == "__main__":
    EditInGimp().run()
