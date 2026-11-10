#!/usr/bin/env bash
# Install everything the book skill needs into ~/.animalbook, without admin rights:
# TinyTeX (LuaLaTeX and the template's packages), and Python 3.10+, Poppler,
# ImageMagick and pytest from conda-forge through micromamba. macOS on Apple Silicon only.
# With --video it also installs what prepare_recording.py needs: ffmpeg and
# mlx-whisper with its speech model (about 3.3 GB more: 1.8 GB of tools, most of
# it PyTorch, which mlx-whisper requires, and 1.5 GB of model).
# Safe to run again. Undo everything with remove_env.sh.
set -euo pipefail

ENV_DIR="$HOME/.animalbook"
TINYTEX_VERSION="v2026.11"
MARKER="# added by animalbook setup_env.sh"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
WHISPER_MODEL="mlx-community/whisper-large-v3-turbo"
VIDEO=0
[ "${1:-}" = "--video" ] && VIDEO=1

if [ "$(uname -s)-$(uname -m)" != "Darwin-arm64" ]; then
  echo "setup_env.sh supports only macOS on Apple Silicon" >&2
  exit 1
fi
mkdir -p "$ENV_DIR/bin"

echo "== LaTeX (TinyTeX $TINYTEX_VERSION)"
TLMGR="$ENV_DIR/TinyTeX/bin/universal-darwin/tlmgr"
if [ ! -x "$TLMGR" ]; then
  curl -fsSL "https://github.com/rstudio/tinytex-releases/releases/download/$TINYTEX_VERSION/TinyTeX-1-darwin-$TINYTEX_VERSION.tar.xz" \
    | tar -xJ -C "$ENV_DIR"
fi
# tlmgr refuses to install anything while a newer tlmgr exists.
"$TLMGR" update --self
# Every \RequirePackage of tex/animalbook.sty, plus what tcolorbox's skins and breakable load.
"$TLMGR" install luatex makeindex fontspec luaotfload titlesec tcolorbox environ trimspaces tikzfill \
  pdfcol enumitem imakeidx pdfpages fancyhdr caption listings booktabs tools microtype \
  etoolbox iftex xcolor pgf amsmath amsfonts hyperref graphics
"$TLMGR" option sys_bin "$ENV_DIR/bin"
"$TLMGR" path add

echo "== Python, Poppler, ImageMagick and pytest (micromamba)"
export MAMBA_ROOT_PREFIX="$ENV_DIR/mamba"
MAMBA="$ENV_DIR/bin/micromamba"
if [ ! -x "$MAMBA" ]; then
  curl -fsSL https://micro.mamba.pm/api/micromamba/osx-arm64/latest | tar -xj -C "$ENV_DIR" bin/micromamba
fi
if [ -d "$ENV_DIR/conda" ]; then
  "$MAMBA" install -y -p "$ENV_DIR/conda" -c conda-forge "python>=3.10" poppler imagemagick pytest
else
  "$MAMBA" create -y -p "$ENV_DIR/conda" -c conda-forge "python>=3.10" poppler imagemagick pytest
fi
# The download cache is only needed while installing.
"$MAMBA" clean -a -y
# Link only the commands the skill calls, so nothing else of the conda env lands on PATH.
for name in pdftoppm pdfinfo pdftotext pytest; do
  ln -sf "$ENV_DIR/conda/bin/$name" "$ENV_DIR/bin/$name"
done
# ImageMagick 7 answers to `convert` when called by that name.
ln -sf "$ENV_DIR/conda/bin/magick" "$ENV_DIR/bin/convert"

if [ "$VIDEO" = 1 ]; then
  echo "== Video: ffmpeg and mlx-whisper"
  # Its own env: mlx publishes wheels for a few Python versions only.
  if [ ! -d "$ENV_DIR/whisper" ]; then
    "$MAMBA" create -y -p "$ENV_DIR/whisper" -c conda-forge python=3.12 ffmpeg pip
  fi
  "$ENV_DIR/whisper/bin/python3" -m pip install --quiet --upgrade --no-cache-dir mlx-whisper
  "$MAMBA" clean -a -y
  for name in ffmpeg ffprobe mlx_whisper; do
    ln -sf "$ENV_DIR/whisper/bin/$name" "$ENV_DIR/bin/$name"
  done
  # The model goes inside the env (not ~/.cache) so remove_env.sh removes it too.
  HF_HOME="$ENV_DIR/models" "$ENV_DIR/whisper/bin/python3" -c \
    "from huggingface_hub import snapshot_download; snapshot_download('$WHISPER_MODEL')"
fi

echo "== PATH"
if ! grep -qF "$MARKER" "$HOME/.zshrc" 2>/dev/null; then
  printf '\nexport PATH="%s:$PATH"  %s\n' "$ENV_DIR/bin" "$MARKER" >> "$HOME/.zshrc"
  echo "added $ENV_DIR/bin to PATH in ~/.zshrc (open a new terminal)"
fi

PATH="$ENV_DIR/bin:$PATH" "$ENV_DIR/conda/bin/python3" "$SCRIPTS/check_deps.py"
