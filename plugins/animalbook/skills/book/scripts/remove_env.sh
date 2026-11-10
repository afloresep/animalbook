#!/usr/bin/env bash
# Remove everything setup_env.sh installed: the ~/.animalbook folder and its PATH
# line in ~/.zshrc. Books already written stay where they are.
set -euo pipefail

ENV_DIR="$HOME/.animalbook"
MARKER="# added by animalbook setup_env.sh"

rm -rf "$ENV_DIR"
if [ -f "$HOME/.zshrc" ]; then
  # Write back in place so a symlinked ~/.zshrc stays a symlink.
  kept="$(grep -vF "$MARKER" "$HOME/.zshrc" || true)"
  printf '%s\n' "$kept" > "$HOME/.zshrc"
fi
# micromamba records every environment it creates in ~/.conda and ~/.mamba.
# Drop our entry, and the folders only when nothing else is in them.
envs="$HOME/.conda/environments.txt"
if [ -f "$envs" ]; then
  kept="$(grep -vF "$ENV_DIR/" "$envs" || true)"
  if [ -n "$kept" ]; then printf '%s\n' "$kept" > "$envs"; else rm "$envs"; fi
fi
rmdir "$HOME/.conda" 2>/dev/null || true
rm -f "$HOME/.mamba/pkgs/urls.txt"
rmdir "$HOME/.mamba/pkgs" "$HOME/.mamba" 2>/dev/null || true
echo "removed $ENV_DIR and its PATH line in ~/.zshrc"
