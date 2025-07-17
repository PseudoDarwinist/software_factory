# Goose AI Setup Instructions

## Problem
The ingestion worker was failing with:
```
npm ERR! 404 Not Found - GET https://registry.npmjs.org/@block%2fcodename-goose - Not found
```

## Solution
Block's Goose AI is **not an npm package**. It's distributed as a binary via their download script or Homebrew.

## Installation Methods

### Method 1: Download Script (Recommended)
```bash
# Install latest version on macOS
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | bash

# Or install without interactive configuration
curl -fsSL https://github.com/block/goose/releases/download/stable/download_cli.sh | CONFIGURE=false bash
```

### Method 2: Homebrew
```bash
# Install via Homebrew (if available)
brew install goose
```

## Configuration
After installation, configure Goose:
```bash
# Set provider via environment variable
export GOOSE_PROVIDER=claude-code

# Or configure interactively
goose configure
```

You'll be prompted to:
1. Select a provider (choose `claude-code` for Claude integration)
2. Enter your API key if required

## Verification
Test that Goose is installed correctly:
```bash
goose --help
```

## Changes Made
1. Updated `mission-control/worker/ingestionWorker.js`:
   - Changed `GOOSE_CMD` from `'npx'` to `'goose'`
   - Removed `'--yes', '@block/codename-goose'` from args
   - Temporarily implemented manual system map generation since Goose requires interactive sessions

## Current Status
The ingestion worker now uses a **manual system map generation** approach because:
- Goose requires interactive sessions for operation
- No non-interactive/batch mode currently available
- Basic file system scanning provides minimal repository structure info

## Next Steps
1. Install Goose AI using the download script above
2. Configure with your Claude API key: `export GOOSE_PROVIDER=claude-code`
3. The ingestion worker will now run without the npm error
4. Future: Implement proper Goose integration when non-interactive mode becomes available