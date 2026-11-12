#!/usr/bin/env bash
# Install what the book skill needs and this Mac lacks into ~/.animalbook, with no
# admin rights:
# - LaTeX: TinyTeX with the packages of tex/animalbook.sty, unless another TeX
#   with lualatex is already installed. A few hundred MB, not the 6 GB of MacTeX.
# - Poppler and ImageMagick from conda-forge through micromamba, only when they
#   are missing (with Homebrew, `brew install poppler imagemagick` does the same).
# For recordings (prepare_recording.py), add one:
#   --recordings  ffmpeg only, when every recording comes with a .vtt transcript.
#   --whisper     ffmpeg, whisper.cpp and a 5-bit copy of Whisper large-v3-turbo
#                 (about 0.6 GB).
# Safe to run again. Undo everything with remove_env.sh.
set -euo pipefail

ENV_DIR="$HOME/.animalbook"
TINYTEX_VERSION="v2026.11"
MARKER="# added by animalbook setup_env.sh"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
MODEL="$ENV_DIR/models/ggml-large-v3-turbo-q5_0.bin"

RECORDINGS=0
WHISPER=0
case "$#:${1:-}" in
  0:) ;;
  1:--recordings) RECORDINGS=1 ;;
  1:--whisper) RECORDINGS=1 WHISPER=1 ;;
  *)
    echo "usage: setup_env.sh [--recordings | --whisper]" >&2
    exit 2
    ;;
esac

if [ "$(uname -s)" != "Darwin" ]; then
  echo "setup_env.sh supports only macOS; on Linux use the apt commands check_deps.py prints" >&2
  exit 1
fi
case "$(uname -m)" in
  arm64) PLATFORM="osx-arm64" ;;
  *) PLATFORM="osx-64" ;;
esac
has() { command -v "$1" >/dev/null 2>&1; }
mkdir -p "$ENV_DIR/bin"

TLMGR="$ENV_DIR/TinyTeX/bin/universal-darwin/tlmgr"
if [ -x "$TLMGR" ] || ! has lualatex; then
  echo "== LaTeX (TinyTeX $TINYTEX_VERSION)"
  if [ ! -x "$TLMGR" ]; then
    curl -fsSL "https://github.com/rstudio/tinytex-releases/releases/download/$TINYTEX_VERSION/TinyTeX-1-darwin-$TINYTEX_VERSION.tar.xz" \
      | tar -xJ -C "$ENV_DIR"
  fi
  # tlmgr refuses to install anything while a newer tlmgr exists.
  "$TLMGR" update --self
  # Every \RequirePackage of tex/animalbook.sty, plus what tcolorbox's skins and breakable load.
  "$TLMGR" install luatex makeindex fontspec luaotfload geometry titlesec tcolorbox environ trimspaces tikzfill \
    pdfcol enumitem imakeidx pdfpages fancyhdr caption listings booktabs tools microtype \
    etoolbox iftex xcolor pgf amsmath amsfonts hyperref graphics
  "$TLMGR" option sys_bin "$ENV_DIR/bin"
  "$TLMGR" path add
else
  echo "== LaTeX: lualatex found, TinyTeX not needed (check_deps.py says what that TeX still lacks)"
fi

# conda-forge packages for whatever is missing. A plain string, not an array:
# macOS bash 3.2 treats an empty array as unset under `set -u`.
PKGS=""
{ has pdftoppm && has pdfinfo; } || PKGS="$PKGS poppler"
has convert || PKGS="$PKGS imagemagick"
if [ "$RECORDINGS" = 1 ]; then
  { has ffmpeg && has ffprobe; } || PKGS="$PKGS ffmpeg"
fi
if [ "$WHISPER" = 1 ]; then
  has whisper-cli || PKGS="$PKGS whisper.cpp"
fi

# Keep everything micromamba writes, its package cache too, inside ~/.animalbook.
export MAMBA_ROOT_PREFIX="$ENV_DIR/mamba"
export CONDA_PKGS_DIRS="$ENV_DIR/mamba/pkgs"
# micromamba 2 keeps its repodata index in ~/.cache/conda otherwise.
export XDG_CACHE_HOME="$ENV_DIR/mamba/cache"
MAMBA="$ENV_DIR/bin/micromamba"

if [ -n "$PKGS" ]; then
  echo "== conda-forge:$PKGS"
  if [ ! -x "$MAMBA" ]; then
    curl -fsSL "https://micro.mamba.pm/api/micromamba/$PLATFORM/latest" | tar -xj -C "$ENV_DIR" bin/micromamba
  fi
  # PKGS is unquoted on purpose: it is a space-separated list.
  # conda-meta exists only once an env is complete; anything else is a broken earlier try.
  if [ -d "$ENV_DIR/conda/conda-meta" ]; then
    "$MAMBA" install -y -p "$ENV_DIR/conda" -c conda-forge $PKGS
  else
    rm -rf "$ENV_DIR/conda"
    "$MAMBA" create -y -p "$ENV_DIR/conda" -c conda-forge $PKGS
  fi
  # The download cache is only needed while installing.
  "$MAMBA" clean -a -y
  # Link only the commands the skill calls, so nothing else of the env lands on PATH.
  for name in pdftoppm pdfinfo pdftotext ffmpeg ffprobe whisper-cli; do
    if [ -x "$ENV_DIR/conda/bin/$name" ]; then ln -sf "$ENV_DIR/conda/bin/$name" "$ENV_DIR/bin/$name"; fi
  done
  # ImageMagick 7 answers to `convert` when called by that name.
  if [ -x "$ENV_DIR/conda/bin/magick" ]; then ln -sf "$ENV_DIR/conda/bin/magick" "$ENV_DIR/bin/convert"; fi
fi

if [ "$WHISPER" = 1 ] && [ ! -f "$MODEL" ]; then
  echo "== Whisper model for whisper.cpp (about 0.6 GB)"
  mkdir -p "$(dirname "$MODEL")"
  curl -fL --progress-bar -o "$MODEL.part" "$MODEL_URL"
  mv "$MODEL.part" "$MODEL"
fi

echo "== PATH"
if ! grep -qF "$MARKER" "$HOME/.zshrc" 2>/dev/null; then
  printf '\nexport PATH="%s:$PATH"  %s\n' "$ENV_DIR/bin" "$MARKER" >> "$HOME/.zshrc"
  echo "added $ENV_DIR/bin to PATH in ~/.zshrc (open a new terminal)"
fi

PATH="$ENV_DIR/bin:$PATH" python3 "$SCRIPTS/check_deps.py"
