#!/bin/sh
# Install both halves for the current user, by symlinks: the Inkscape
# extension into Inkscape's extensions folder, the GIMP 3 plug-in into
# GIMP's plug-ins folder. --uninstall removes them.
#
# Copyright 2026 David
# SPDX-License-Identifier: GPL-3.0-or-later
set -eu
repo=$(cd "$(dirname "$0")/.." && pwd)
inkscape_dir=${INKSCAPE_EXTENSIONS_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/inkscape/extensions}
gimp_version=$(gimp-console-3.2 --version 2>/dev/null | grep -o '3\.[0-9]*' | head -1 || true)
gimp_dir=${GIMP_PLUGINS_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/GIMP/${gimp_version:-3.2}/plug-ins}
if [ "${1:-}" = --uninstall ]; then
    rm -rf "$inkscape_dir/edit-in-gimp" "$gimp_dir/inkscape-link"
    echo "removed"
    exit 0
fi
mkdir -p "$inkscape_dir/edit-in-gimp" "$gimp_dir"
for f in edit_in_gimp.inx edit_in_gimp.py; do
    ln -sf "$repo/inkscape/$f" "$inkscape_dir/edit-in-gimp/$f"
done
ln -sfn "$repo/gimp/inkscape-link" "$gimp_dir/inkscape-link"
echo "Inkscape: Extensions > Images > Edit in GIMP ($inkscape_dir/edit-in-gimp)"
echo "GIMP:     File > Inkscape Link > Send to Inkscape ($gimp_dir/inkscape-link)"
echo "Restart both."
