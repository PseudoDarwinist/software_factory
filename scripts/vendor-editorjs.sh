#!/usr/bin/env bash
set -euo pipefail

# Vendor Editor.js core, plugins, and Mermaid locally to avoid CDN dependencies.
# Usage:
#   bash scripts/vendor-editorjs.sh
#
# This script tries jsDelivr first, then unpkg as a fallback.
# If any asset fails to download from CDNs, it falls back to npm to fetch UMD builds
# and copies them into frontend/vendor.

ROOT_DIR="$(cd "$(dirname "$0")"/.. && pwd)"
BASE="$ROOT_DIR/frontend/vendor"
mkdir -p "$BASE/editorjs" "$BASE/mermaid"

fetch() {
  local url="$1" out="$2"
  echo "Fetching $url -> $out"
  curl -L --fail --retry 3 --retry-delay 2 -o "$out" "$url" 2>/dev/null || return 1
}

try_candidates() {
  local pkg="$1" ver="$2" out="$3"; shift 3
  local candidates=("$@")
  local cdn_base_jsdelivr="https://cdn.jsdelivr.net/npm"
  local cdn_base_unpkg="https://unpkg.com"

  for path in "${candidates[@]}"; do
    if fetch "$cdn_base_jsdelivr/$pkg@$ver/$path" "$out"; then return 0; fi
    if fetch "$cdn_base_unpkg/$pkg@$ver/$path" "$out"; then return 0; fi
  done
  return 1
}

ensure_present() {
  local file="$1"
  [[ -s "$file" ]]
}

npm_vendor() {
  if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found; cannot perform npm fallback. Please install Node.js/npm or download assets manually." >&2
    return 1
  fi
  local TMP="$ROOT_DIR/scripts/.vendor_tmp"
  rm -rf "$TMP"
  mkdir -p "$TMP"
  cat > "$TMP/package.json" <<'JSON'
{
  "name": "vendor-editorjs-tmp",
  "private": true,
  "license": "UNLICENSED",
  "dependencies": {}
}
JSON
  pushd "$TMP" >/dev/null
  echo "Installing packages via npm (offline vendor fallback)..."
  npm install --silent --no-progress \
    @editorjs/editorjs@"$EJS_VER" \
    @editorjs/header@"$HDR_VER" \
    @editorjs/paragraph@"$PARA_VER" \
    @editorjs/list@"$LIST_VER" \
    @editorjs/quote@"$QUOTE_VER" \
    @editorjs/table@"$TABLE_VER" \
    @editorjs/raw@"$RAW_VER" \
    @editorjs/delimiter@"$DELIM_VER" \
    mermaid@"$MERMAID_VER" >/dev/null
  popd >/dev/null

  # Copy UMD builds
  cp -f "$TMP/node_modules/@editorjs/editorjs/dist/editor.js" "$BASE/editorjs/editorjs.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/@editorjs/header/dist/header.js" "$BASE/editorjs/header.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/@editorjs/paragraph/dist/paragraph.js" "$BASE/editorjs/paragraph.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/@editorjs/list/dist/list.js" "$BASE/editorjs/list.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/@editorjs/quote/dist/quote.js" "$BASE/editorjs/quote.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/@editorjs/table/dist/table.js" "$BASE/editorjs/table.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/@editorjs/raw/dist/raw.js" "$BASE/editorjs/raw.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/@editorjs/delimiter/dist/delimiter.js" "$BASE/editorjs/delimiter.js" 2>/dev/null || true
  cp -f "$TMP/node_modules/mermaid/dist/mermaid.min.js" "$BASE/mermaid/mermaid.min.js" 2>/dev/null || true

  rm -rf "$TMP"
}

# Versions pinned for stability (adjust if needed)
EJS_VER="2.29.1"
HDR_VER="2.8.1"
PARA_VER="2.8.1"
LIST_VER="1.8.0"
QUOTE_VER="2.4.0"
TABLE_VER="2.2.1"
RAW_VER="2.4.0"
DELIM_VER="1.3.0"
MERMAID_VER="10.9.1"

NEED_NPM=0

# Editor.js core (UMD/IIFE)
try_candidates "@editorjs/editorjs" "$EJS_VER" "$BASE/editorjs/editorjs.js" \
  "dist/editor.js" \
  "dist/editor.min.js" || NEED_NPM=1

# Plugins (UMD/IIFE builds)
try_candidates "@editorjs/header" "$HDR_VER" "$BASE/editorjs/header.js" \
  "dist/header.js" "dist/header.min.js" "dist/bundle.js" || NEED_NPM=1

try_candidates "@editorjs/paragraph" "$PARA_VER" "$BASE/editorjs/paragraph.js" \
  "dist/paragraph.js" "dist/paragraph.min.js" "dist/bundle.js" || NEED_NPM=1

try_candidates "@editorjs/list" "$LIST_VER" "$BASE/editorjs/list.js" \
  "dist/list.js" "dist/list.min.js" "dist/bundle.js" || NEED_NPM=1

try_candidates "@editorjs/quote" "$QUOTE_VER" "$BASE/editorjs/quote.js" \
  "dist/quote.js" "dist/quote.min.js" "dist/bundle.js" || NEED_NPM=1

try_candidates "@editorjs/table" "$TABLE_VER" "$BASE/editorjs/table.js" \
  "dist/table.js" "dist/table.min.js" "dist/bundle.js" || NEED_NPM=1

try_candidates "@editorjs/raw" "$RAW_VER" "$BASE/editorjs/raw.js" \
  "dist/raw.js" "dist/raw.min.js" "dist/bundle.js" || NEED_NPM=1

try_candidates "@editorjs/delimiter" "$DELIM_VER" "$BASE/editorjs/delimiter.js" \
  "dist/delimiter.js" "dist/delimiter.min.js" "dist/bundle.js" || NEED_NPM=1

# Mermaid
try_candidates "mermaid" "$MERMAID_VER" "$BASE/mermaid/mermaid.min.js" \
  "dist/mermaid.min.js" "dist/mermaid.js" || NEED_NPM=1

# If any file failed, try npm fallback for missing ones
if [[ "$NEED_NPM" -eq 1 ]]; then
  echo "One or more assets missing from CDN. Attempting npm fallback..."
  npm_vendor || true
fi

# Validate presence of all required files
missing=0
for f in \
  "$BASE/editorjs/editorjs.js" \
  "$BASE/editorjs/header.js" \
  "$BASE/editorjs/paragraph.js" \
  "$BASE/editorjs/list.js" \
  "$BASE/editorjs/quote.js" \
  "$BASE/editorjs/table.js" \
  "$BASE/editorjs/raw.js" \
  "$BASE/editorjs/delimiter.js" \
  "$BASE/mermaid/mermaid.min.js"; do
  if ! ensure_present "$f"; then
    echo "Missing required file: $f" >&2
    missing=1
  fi
done

if [[ "$missing" -ne 0 ]]; then
  echo "Some vendor assets are missing. Please check your network or run this script again." >&2
  exit 1
fi

# Summary
printf "\nVendored files:\n"
ls -1 "$BASE/editorjs" "$BASE/mermaid" | sed 's/^/  /'

echo "\nDone. All required Editor.js plugins and Mermaid are vendored locally."

