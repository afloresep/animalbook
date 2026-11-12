#!/usr/bin/env bash
# Install what the book skill needs and this Mac lacks into ~/.animalbook, with no
# admin rights:
# - LaTeX: TinyTeX with the packages of tex/animalbook.sty, unless another TeX
#   with lualatex is already installed. A few hundred MB, not the 6 GB of MacTeX.
# - Poppler and ImageMagick from conda-forge through micromamba, only when they
#   are missing (with Homebrew, `brew install poppler imagemagick` does the same).
# For recordings (prepare_recording.py), add one:
#   --recordings     ffmpeg only, when every recording comes with a .vtt transcript.
#   --whisper light  ffmpeg, whisper.cpp and a 5-bit copy of Whisper large-v3-turbo
#                    (about 0.6 GB). Any Mac.
#   --whisper full   ffmpeg and mlx-whisper with the full large-v3-turbo model (about
#                    3.3 GB, most of it PyTorch, which mlx-whisper requires). Apple
#                    Silicon only.
# Safe to run again. Undo everything with remove_env.sh.
set -euo pipefail

ENV_DIR="$HOME/.animalbook"
TINYTEX_VERSION="v2026.11"
MARKER="# added by animalbook setup_env.sh"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
FULL_MODEL="mlx-community/whisper-large-v3-turbo"
LIGHT_MODEL_URL="https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
LIGHT_MODEL="$ENV_DIR/models/ggml-large-v3-turbo-q5_0.bin"
USAGE="usage: setup_env.sh [--recordings | --whisper light | --whisper full]"

RECORDINGS=0
WHISPER=""
case "${1:-}" in
  "") ;;
  --recordings) RECORDINGS=1 ;;
  --whisper)
    WHISPER="${2:-}"
    RECORDINGS=1
    if [ "$WHISPER" != "light" ] && [ "$WHISPER" != "full" ]; then
      echo "$USAGE" >&2
      exit 2
    fi
    ;;
  *)
    echo "$USAGE" >&2
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
if [ "$WHISPER" = "full" ] && [ "$PLATFORM" != "osx-arm64" ]; then
  echo "--whisper full needs Apple Silicon; use --whisper light" >&2
  exit 1
fi
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
if [ "$WHISPER" = "light" ]; then
  has whisper-cli || PKGS="$PKGS whisper.cpp"
fi

# Keep everything micromamba writes, its package cache too, inside ~/.animalbook.
export MAMBA_ROOT_PREFIX="$ENV_DIR/mamba"
export CONDA_PKGS_DIRS="$ENV_DIR/mamba/pkgs"
# micromamba 2 keeps its repodata index in ~/.cache/conda otherwise.
export XDG_CACHE_HOME="$ENV_DIR/mamba/cache"
MAMBA="$ENV_DIR/bin/micromamba"
get_micromamba() {
  if [ ! -x "$MAMBA" ]; then
    curl -fsSL "https://micro.mamba.pm/api/micromamba/$PLATFORM/latest" | tar -xj -C "$ENV_DIR" bin/micromamba
  fi
}

if [ -n "$PKGS" ]; then
  echo "== conda-forge:$PKGS"
  get_micromamba
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

if [ "$WHISPER" = "light" ] && [ ! -f "$LIGHT_MODEL" ]; then
  echo "== Whisper model for whisper.cpp (about 0.6 GB)"
  mkdir -p "$(dirname "$LIGHT_MODEL")"
  curl -fL --progress-bar -o "$LIGHT_MODEL.part" "$LIGHT_MODEL_URL"
  mv "$LIGHT_MODEL.part" "$LIGHT_MODEL"
fi

if [ "$WHISPER" = "full" ]; then
  echo "== mlx-whisper"
  get_micromamba
  # Its own env: mlx publishes wheels for a few Python versions only.
  if [ ! -x "$ENV_DIR/whisper/bin/python3" ]; then
    rm -rf "$ENV_DIR/whisper"
    "$MAMBA" create -y -p "$ENV_DIR/whisper" -c conda-forge python=3.12 pip
  fi
  "$ENV_DIR/whisper/bin/python3" -m pip install --quiet --upgrade --no-cache-dir mlx-whisper
  "$MAMBA" clean -a -y
  ln -sf "$ENV_DIR/whisper/bin/mlx_whisper" "$ENV_DIR/bin/mlx_whisper"
  # The model goes inside ~/.animalbook (not ~/.cache) so remove_env.sh removes it
  # too; prepare_recording.py looks for it there.
  HF_HOME="$ENV_DIR/models/hf" "$ENV_DIR/whisper/bin/python3" -c \
    "from huggingface_hub import snapshot_download; snapshot_download('$FULL_MODEL')"
fi

echo "== PATH"
if ! grep -qF "$MARKER" "$HOME/.zshrc" 2>/dev/null; then
  printf '\nexport PATH="%s:$PATH"  %s\n' "$ENV_DIR/bin" "$MARKER" >> "$HOME/.zshrc"
  echo "added $ENV_DIR/bin to PATH in ~/.zshrc (open a new terminal)"
fi

PATH="$ENV_DIR/bin:$PATH" python3 "$SCRIPTS/check_deps.py"
