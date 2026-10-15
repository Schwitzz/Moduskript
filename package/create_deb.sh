#!/bin/bash
# Builds the Moduskript .deb package without requiring sudo (--root-owner-group)
# and places the compiled .deb in releases/.
# Usage: ./package/create_deb.sh [Version] [PkgNumber]
set -e

ScriptPath="$( cd "$(dirname "$0")" ; pwd -P )"
Root="$( cd "$ScriptPath/.." ; pwd -P )"
WorkspaceRoot="$( cd "$Root/.." ; pwd -P )"

Version=$(grep -E "__version__.*\".*\"" "$Root/manuskript/version.py" | cut -d\" -f2)
AppVersion=${1:-$Version}
PkgNumber=${2:-1}
PkgVersion="${AppVersion}-moduskript${PkgNumber}"

BuildDir="/tmp/opencode/moduskript_deb_build"
PkgDir="$BuildDir/pkg"
ReleasesDir="$Root/releases"
WorkspaceReleasesDir="$WorkspaceRoot/releases"

rm -rf "$BuildDir"
mkdir -p "$PkgDir/DEBIAN" "$PkgDir/usr/bin" "$PkgDir/usr/share/applications" "$ReleasesDir" "$WorkspaceReleasesDir"

echo "Copying Moduskript application files..."
rsync -a \
  --exclude=.git \
  --exclude=dist \
  --exclude=releases \
  --exclude=rpmbuild \
  --exclude=snap \
  --exclude=package \
  --exclude=__pycache__ \
  --exclude=.pytest_cache \
  --exclude=.github \
  --include='*.msk' \
  --exclude-from="$Root/.gitignore" \
  "$Root/" "$PkgDir/usr/share/manuskript/"

cp "$ScriptPath/create_deb/manuskript" "$PkgDir/usr/bin/manuskript"
ln -sf manuskript "$PkgDir/usr/bin/moduskript"
cp "$ScriptPath/create_deb/manuskript.desktop" "$PkgDir/usr/share/applications/manuskript.desktop"

for s in 16 32 64 128 256 512; do
  mkdir -p "$PkgDir/usr/share/icons/hicolor/${s}x${s}/apps"
  cp "$Root/icons/Manuskript/icon-${s}px.png" "$PkgDir/usr/share/icons/hicolor/${s}x${s}/apps/manuskript.png"
done

find "$PkgDir" -type d -exec chmod 0755 {} +
find "$PkgDir" -type f ! -perm -u+x -exec chmod 0644 {} +
chmod 0755 "$PkgDir/usr/bin/manuskript"

SZ=$(du -sk "$PkgDir" | cut -f1)
cat > "$PkgDir/DEBIAN/control" << EOC
Package: moduskript
Version: $PkgVersion
Maintainer: Schwitzz <https://github.com/Schwitzz/Moduskript>
Description: Moduskript — AI-assisted novel writing studio with 32 themes, Whiteboard, and Web App.
 Moduskript (derived from Manuskript) is an open-source tool for writers featuring:
  - Integrated AI Assistant (local llama.cpp, OpenAI, Anthropic, Google Gemini)
  - 32 WCAG-checked colour schemes with live theme switching
  - Native multi-board Whiteboard with shapes, sticky notes, 4 connector styles, and colors
  - Modernized Outline (Chapters, indented Scenes, Associated Notes, Tree/Table views)
  - Markdown Writing Space with live Readable Mode vs. MD Code toggle and FormatBar
  - Integrated background Web App server with commingled project storage
Section: editors
Priority: optional
Installed-Size: $SZ
Architecture: all
Conflicts: manuskript, manuskript-ai
Replaces: manuskript, manuskript-ai
Provides: manuskript, manuskript-ai
Homepage: https://github.com/Schwitzz/Moduskript
Depends: python3, python3-pyqt5, python3-pyqt5.qtwebengine | python3-pyqt5.qtwebkit, libqt5svg5, python3-lxml, zlib1g, python3-enchant, python3-markdown, python3-requests, pandoc
Suggests: texlive-latex-recommended
EOC

DebName="moduskript_${PkgVersion}_all.deb"
dpkg-deb --root-owner-group -Zxz -b "$PkgDir" "$ReleasesDir/$DebName"
cp "$ReleasesDir/$DebName" "$WorkspaceReleasesDir/$DebName"
rm -rf "$BuildDir"

echo "Built package:"
ls -lh "$ReleasesDir/$DebName" "$WorkspaceReleasesDir/$DebName"
