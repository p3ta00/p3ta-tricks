#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# p3ta-tricks — offline install script
# Sets up a fully self-contained offline pentest reference wiki.
# Run once before going dark. Tested on Arch/CachyOS, Debian/Kali/Ubuntu,
# Fedora/RHEL, and macOS (Homebrew).
#
# Usage:
#   chmod +x install.sh && ./install.sh
#   TOOLS_DIR=/path/to/tools ./install.sh   # custom tools location
#   ./install.sh --no-tools                 # skip tool deps, wiki only
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLS_DIR="${TOOLS_DIR:-$(dirname "$SCRIPT_DIR")/p3ta-tricks-offline/tools}"
SKIP_TOOLS=0
VENV_DIR="$SCRIPT_DIR/.venv"

# ── Parse args ────────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-tools) SKIP_TOOLS=1 ;;
    --help|-h)
      echo "Usage: $0 [--no-tools]"
      echo "  --no-tools   Only install wiki dependencies, skip pentest tool setup"
      exit 0 ;;
  esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[+]${NC} $*"; }
info() { echo -e "${CYAN}[*]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
die()  { echo -e "${RED}[✗]${NC} $*"; exit 1; }

echo -e "${BOLD}"
echo "  ██████╗ ██████╗ ████████╗ █████╗       ████████╗██████╗ ██╗ ██████╗██╗  ██╗███████╗"
echo "  ██╔══██╗╚════██╗╚══██╔══╝██╔══██╗      ╚══██╔══╝██╔══██╗██║██╔════╝██║ ██╔╝██╔════╝"
echo "  ██████╔╝ █████╔╝    ██║   ███████║         ██║   ██████╔╝██║██║     █████╔╝ ███████╗"
echo "  ██╔═══╝  ╚═══██╗    ██║   ██╔══██║         ██║   ██╔══██╗██║██║     ██╔═██╗ ╚════██║"
echo "  ██║     ██████╔╝    ██║   ██║  ██║         ██║   ██║  ██║██║╚██████╗██║  ██╗███████║"
echo "  ╚═╝     ╚═════╝     ╚═╝   ╚═╝  ╚═╝         ╚═╝   ╚═╝  ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝"
echo -e "${NC}"
echo "  Offline Install — $(date '+%Y-%m-%d')"
echo ""

# ── Detect OS / package manager ───────────────────────────────────────────────
detect_pkg() {
  if command -v pacman &>/dev/null; then echo "arch"
  elif command -v apt-get &>/dev/null; then echo "debian"
  elif command -v dnf &>/dev/null; then echo "fedora"
  elif command -v brew &>/dev/null; then echo "macos"
  else echo "unknown"
  fi
}
PKG=$(detect_pkg)
info "Detected package manager: ${BOLD}${PKG}${NC}"

# ── System package installer helper ───────────────────────────────────────────
sys_install() {
  case "$PKG" in
    arch)   sudo pacman -S --noconfirm --needed "$@" ;;
    debian) sudo apt-get install -y "$@" ;;
    fedora) sudo dnf install -y "$@" ;;
    macos)  brew install "$@" ;;
    *)      warn "Unknown package manager — install manually: $*" ;;
  esac
}

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — Python 3.11+
# ─────────────────────────────────────────────────────────────────────────────
info "Checking Python..."
if ! command -v python3 &>/dev/null; then
  info "Installing Python 3..."
  case "$PKG" in
    arch)   sys_install python ;;
    debian) sys_install python3 python3-pip python3-venv ;;
    fedora) sys_install python3 python3-pip ;;
    macos)  sys_install python@3.12 ;;
  esac
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
info "Python version: $PY_VER"
if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
  ok "Python $PY_VER is sufficient"
else
  die "Python 3.9+ required, found $PY_VER"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — pip
# ─────────────────────────────────────────────────────────────────────────────
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null 2>&1; then
  info "Installing pip..."
  case "$PKG" in
    arch)   sys_install python-pip ;;
    debian) sys_install python3-pip ;;
    fedora) sys_install python3-pip ;;
    macos)  python3 -m ensurepip --upgrade ;;
  esac
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — Create virtualenv and install wiki requirements
# ─────────────────────────────────────────────────────────────────────────────
info "Setting up Python virtual environment at $VENV_DIR ..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR" || {
    # Debian may need python3-venv
    sys_install python3-venv 2>/dev/null || true
    python3 -m venv "$VENV_DIR"
  }
  ok "Virtualenv created"
else
  ok "Virtualenv already exists"
fi

VENV_PIP="$VENV_DIR/bin/pip"
VENV_PY="$VENV_DIR/bin/python3"

info "Installing wiki requirements..."
if [ -d "$SCRIPT_DIR/vendor" ] && [ -n "$(ls -A "$SCRIPT_DIR/vendor" 2>/dev/null)" ]; then
  info "vendor/ found — installing offline (no PyPI)"
  # Wheels may live in vendor/ and/or vendor/wheels/ — search both.
  if ! "$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" \
        --no-index \
        --find-links "$SCRIPT_DIR/vendor/" \
        --find-links "$SCRIPT_DIR/vendor/wheels/" --quiet; then
    warn "Offline install from vendor/ failed — falling back to PyPI"
    "$VENV_PIP" install --upgrade pip --quiet || true
    "$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" --quiet
  fi
else
  "$VENV_PIP" install --upgrade pip --quiet
  "$VENV_PIP" install -r "$SCRIPT_DIR/requirements.txt" --quiet
fi
ok "Wiki requirements installed"

# Verify key imports
"$VENV_PY" -c "import flask, markdown, yaml, pygments" && ok "All Python imports verified" || die "Import check failed"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — Verify all static assets are local (no CDN gaps)
# ─────────────────────────────────────────────────────────────────────────────
info "Verifying offline asset completeness..."

STATIC="$SCRIPT_DIR/static"
MISSING=0

check_file() {
  if [ ! -f "$1" ]; then
    warn "MISSING: $1"
    MISSING=$((MISSING+1))
  fi
}

# Critical JS
check_file "$STATIC/js/prism-bundle.min.js"
check_file "$STATIC/js/fuse.min.js"
check_file "$STATIC/js/app.js"
check_file "$STATIC/js/mermaid.min.js"

# CSS
check_file "$STATIC/css/style.css"

# Fonts
check_file "$STATIC/fonts/press-start-2p.css"
check_file "$STATIC/fonts/press-start-2p-latin.woff2"

# Adaptix C2 locally-hosted screenshots (required for offline)
ADAPTIX_IMG_COUNT=$(find "$STATIC/img/adaptix" -name "*.png" -o -name "*.jpg" 2>/dev/null | wc -l)
if [ "$ADAPTIX_IMG_COUNT" -lt 100 ]; then
  warn "Only $ADAPTIX_IMG_COUNT Adaptix images found (expected 190+) — run: python3 scripts/fetch_adaptix_images.py"
else
  ok "$ADAPTIX_IMG_COUNT Adaptix screenshots cached locally"
fi

# Sliver C2 images
check_file "$SCRIPT_DIR/sources/sliver-docs/images/cursed-1.png"
check_file "$SCRIPT_DIR/sources/sliver-docs/images/dns-c2-1.png"

# CyberChef (optional but expected)
if [ ! -f "$STATIC/cyberchef/CyberChef_v11.0.0.html" ]; then
  warn "CyberChef not found at $STATIC/cyberchef/ — the CyberChef tab will show a blank page"
  warn "Download from: https://github.com/gchq/CyberChef/releases"
fi

if [ "$MISSING" -gt 0 ]; then
  die "$MISSING critical static files missing — check the repo is complete"
fi
ok "All critical static assets present"

# Third-party external images (download and locally host)
EXT_IMG_COUNT=$(find "$STATIC/img/external" -type f 2>/dev/null | wc -l)
if [ "$EXT_IMG_COUNT" -lt 100 ]; then
  info "Downloading third-party source images (first run — takes ~2 minutes)..."
  "$VENV_PY" "$SCRIPT_DIR/scripts/fetch_external_images.py" 2>/dev/null && \
    ok "External images downloaded and locally hosted" || \
    warn "Some external images failed to download (unreachable third-party domains)"
else
  ok "$EXT_IMG_COUNT external images already cached in static/img/external/"
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — Verify processed content
# ─────────────────────────────────────────────────────────────────────────────
info "Checking content completeness..."
CONTENT_DIR="$SCRIPT_DIR/content/processed"
PAGE_COUNT=$(find "$CONTENT_DIR" -name "*.json" | wc -l)
NAV_COUNT=$(find "$SCRIPT_DIR/content/nav" -name "*.json" | wc -l)

if [ "$PAGE_COUNT" -lt 3000 ]; then
  warn "Only $PAGE_COUNT processed pages found — expected 3200+. Run: git pull"
else
  ok "$PAGE_COUNT content pages found"
fi
ok "$NAV_COUNT nav files found"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — Tool dependencies (skip with --no-tools)
# ─────────────────────────────────────────────────────────────────────────────
if [ "$SKIP_TOOLS" -eq 1 ]; then
  warn "Skipping tool setup (--no-tools)"
else
  info "Checking pentest tool dependencies..."

  TOOLS_PIP="$TOOLS_DIR/../venv/bin/pip" 2>/dev/null || TOOLS_PIP="$VENV_PIP"

  # Install Python attack tool requirements from tools directory
  if [ -d "$TOOLS_DIR" ]; then
    PYTHON_TOOLS=(
      BloodHound.py bloodyAD Certipy Coercer DonPAPI jwt_tool LaZagne
      ldapdomaindump ldeep lsassy mitm6 MSSqlPwner NetExec PKINITtools
      pyGoldenGMSA pypykatz pywhisker Responder ROADtools sccmhunter
      targetedKerberoast impacket-src
    )
    for tool in "${PYTHON_TOOLS[@]}"; do
      req="$TOOLS_DIR/$tool/requirements.txt"
      if [ -f "$req" ]; then
        info "  Installing deps for $tool..."
        "$VENV_PIP" install -r "$req" --quiet 2>/dev/null || \
          warn "  Some deps for $tool failed — continuing"
      fi
    done
    ok "Tool Python requirements processed"

    # Count available tools
    TOOL_COUNT=$(ls "$TOOLS_DIR" | wc -l)
    ok "$TOOL_COUNT tools found in $TOOLS_DIR"
  else
    warn "TOOLS_DIR not found at $TOOLS_DIR"
    warn "Set TOOLS_DIR env var or place tools at: $TOOLS_DIR"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — Generate start script
# ─────────────────────────────────────────────────────────────────────────────
START_SCRIPT="$SCRIPT_DIR/start-offline.sh"
cat > "$START_SCRIPT" << STARTSCRIPT
#!/usr/bin/env bash
# p3ta-tricks offline launcher — generated by install.sh
set -euo pipefail

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="\$SCRIPT_DIR/.venv/bin/python3"
TOOLS_DIR="\${TOOLS_DIR:-\$(dirname "\$SCRIPT_DIR")/p3ta-tricks-offline/tools}"
PORT="\${PORT:-5001}"
HOST="\${HOST:-127.0.0.1}"

# Validate venv
if [ ! -f "\$VENV_PY" ]; then
  echo "[!] Virtualenv not found. Run: ./install.sh"
  exit 1
fi

export OFFLINE_MODE=1
export TOOLS_DIR="\$TOOLS_DIR"

echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │   p3ta-tricks  —  OFFLINE MODE              │"
echo "  │   http://\${HOST}:\${PORT}                     │"
echo "  │   TOOLS_DIR: \$TOOLS_DIR"
echo "  └─────────────────────────────────────────────┘"
echo ""

cd "\$SCRIPT_DIR"

# Use gunicorn if available for stability, fall back to Flask dev server
if [ -f "\$SCRIPT_DIR/.venv/bin/gunicorn" ]; then
  exec "\$SCRIPT_DIR/.venv/bin/gunicorn" \
    --bind "\${HOST}:\${PORT}" \
    --workers 2 \
    --timeout 60 \
    --access-logfile - \
    app:app
else
  exec "\$VENV_PY" app.py
fi
STARTSCRIPT
chmod +x "$START_SCRIPT"
ok "Start script written to: $START_SCRIPT"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 8 — Network isolation test
# ─────────────────────────────────────────────────────────────────────────────
info "Scanning templates for external URL references..."

EXT_REFS=$(grep -rn "https://\|http://" "$SCRIPT_DIR/templates/" \
  | grep -v "github.com\|gitlab.com\|p3ta-tricks.com\|exploit-db.com\|nvd.nist.gov\|example\|placeholder\|YOUR_\|noopener\|rel=\|{{" \
  | grep -v "<!-\|/\*\|//\s" \
  | { grep "src=\|url(" || true; } \
  | wc -l)

if [ "$EXT_REFS" -gt 0 ]; then
  warn "$EXT_REFS potential external asset references found in templates:"
  grep -rn "https://\|http://" "$SCRIPT_DIR/templates/" \
    | grep -v "github.com\|gitlab.com\|p3ta-tricks.com\|exploit-db.com\|nvd.nist.gov\|example\|placeholder\|YOUR_\|noopener\|rel=\|{{" \
    | { grep "src=\|url(" || true; }
else
  ok "No external asset references found in templates"
fi

# ─────────────────────────────────────────────────────────────────────────────
# DONE
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  Installation complete${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Start the offline wiki:"
echo -e "    ${BOLD}./start-offline.sh${NC}"
echo ""
echo "  Custom port / host:"
echo -e "    ${BOLD}PORT=8080 HOST=0.0.0.0 ./start-offline.sh${NC}"
echo ""
echo "  Custom tools directory:"
echo -e "    ${BOLD}TOOLS_DIR=/path/to/tools ./start-offline.sh${NC}"
echo ""
if [ "$SKIP_TOOLS" -eq 0 ] && [ -d "$TOOLS_DIR" ]; then
  echo "  Tools available: $TOOL_COUNT at $TOOLS_DIR"
  echo ""
fi
