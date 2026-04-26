#!/bin/bash
# Start HouseOfMath.command
# Double-click me from Finder to launch HouseOfMath.
# First launch installs Homebrew + Python + dependencies (5-10 min).
# Every launch after that is instant.

set -e

# cd to the folder this script lives in (so it works no matter where the user puts it)
cd "$(dirname "$0")"

clear
cat <<'BANNER'
================================================
  🧮  HouseOfMath
  Math practice for grades 3-9, in your browser
================================================
BANNER
echo ""

step() { echo ""; echo "→ $1"; }
ok()   { echo "  ✓ $1"; }
fail() { echo ""; echo "  ✗ $1"; echo ""; echo "Press any key to close this window."; read -n 1 -s; exit 1; }

# ----- 1. Homebrew -----
if ! command -v brew >/dev/null 2>&1; then
  step "Installing Homebrew (you'll be asked for your Mac password)..."
  echo "  This is normal — Homebrew is a package manager for macOS."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || fail "Homebrew install failed."
  # Make brew available in this shell session
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
else
  ok "Homebrew already installed."
  # Make sure brew is on PATH for this session even if shell rc didn't load it
  if [ -x /opt/homebrew/bin/brew ] && ! command -v brew >/dev/null 2>&1; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
fi

# ----- 2. Python 3.12 -----
PY=""
for candidate in python3.13 python3.12 python3.11 python3.10; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done

if [ -z "$PY" ]; then
  step "Installing Python 3.12..."
  brew install python@3.12 || fail "Python install failed."
  PY="python3.12"
fi
ok "Using $($PY --version)."

# ----- 3. Virtual environment + install -----
if [ ! -d ".venv" ] || [ ! -x ".venv/bin/houseofmath" ]; then
  step "Setting up HouseOfMath (one-time, ~30 seconds)..."
  rm -rf .venv
  $PY -m venv .venv || fail "Could not create virtual environment."
  # shellcheck source=/dev/null
  source .venv/bin/activate
  pip install --upgrade pip --quiet || fail "pip upgrade failed."
  pip install -e . --quiet || fail "Could not install dependencies."
  ok "Installed."
else
  # shellcheck source=/dev/null
  source .venv/bin/activate
  ok "Already installed."
fi

# ----- 4. Launch -----
step "Opening HouseOfMath in your browser..."
echo ""
echo "  ┌─────────────────────────────────────────────────────────┐"
echo "  │  Keep this window open while you use HouseOfMath.       │"
echo "  │  When you're done, close this window or press Ctrl+C.   │"
echo "  └─────────────────────────────────────────────────────────┘"
echo ""

# `houseofmath run` opens Streamlit which opens the browser automatically
houseofmath run
