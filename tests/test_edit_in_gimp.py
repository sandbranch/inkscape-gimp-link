# Copyright 2026 David
# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for Edit in GIMP (GIMP is not launched). Needs inkex."""

import io
import os
import sys
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "inkscape"))

import inkex
from edit_in_gimp import EditInGimp

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f"
    b"\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00"
    b"\x00IEND\xaeB`\x82"
)


def run(tmp_path, href, monkeypatch, saved=True):
    svg = tmp_path / "d.svg"
    svg.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="10" height="10"><image id="im" width="10" height="10" xlink:href="{href}"/></svg>'
    )
    if saved:
        monkeypatch.setenv("DOCUMENT_PATH", str(svg))
    else:
        # Inkscape passes an empty DOCUMENT_PATH for a drawing never saved
        monkeypatch.setenv("DOCUMENT_PATH", "")
    out = io.BytesIO()
    EditInGimp().run(["--id=im", "--launch=false", str(svg)], output=out)
    return out.getvalue()


def test_linked_image_is_left_alone(tmp_path, monkeypatch):
    (tmp_path / "pic.png").write_bytes(PNG)
    assert (
        run(tmp_path, "pic.png", monkeypatch) == b""
    )  # nothing changed, nothing written


def test_missing_linked_image(tmp_path, monkeypatch, capsys):
    with pytest.raises(SystemExit):
        run(tmp_path, "gone.png", monkeypatch)
    assert "missing" in capsys.readouterr().err


def test_embedded_needs_a_saved_drawing(tmp_path, monkeypatch, capsys):
    import base64

    uri = "data:image/png;base64," + base64.b64encode(PNG).decode()
    with pytest.raises(SystemExit):
        run(tmp_path, uri, monkeypatch, saved=False)
    assert "Save the drawing first" in capsys.readouterr().err


def test_newer_image_than_layers_warns(tmp_path, monkeypatch, capsys):
    (tmp_path / "pic.png.xcf").write_bytes(b"gimp xcf v011\0")
    time.sleep(1.1)
    (tmp_path / "pic.png").write_bytes(PNG)
    os.utime(tmp_path / "pic.png", (time.time() + 5, time.time() + 5))
    run(tmp_path, "pic.png", monkeypatch)
    assert "changed after GIMP last saved" in capsys.readouterr().err


def test_embedded_is_extracted_and_linked(tmp_path, monkeypatch):
    import base64

    uri = "data:image/png;base64," + base64.b64encode(PNG).decode()
    out = run(tmp_path, uri, monkeypatch)
    doc = inkex.load_svg(io.BytesIO(out)).getroot()
    assert doc.getElementById("im").get("xlink:href") == "d_images/im.png"
    assert (tmp_path / "d_images" / "im.png").read_bytes() == PNG
