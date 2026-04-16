# FileForge Web UI

This directory contains the frontend static files for the FileForge web interface.

## Files

- `index.html` - Single-page application with scan dashboard, file table, filters, and modals

## Features

- **Dashboard Stats**: Total files, duplicates, stale files, categories
- **Directory Scan**: Drag-and-drop or choose directory to scan
- **File Table**: View all scanned files with details
- **Filters**: Search, category filter, status filter (normal/duplicate/stale)
- **Tabs**: All Files, Duplicates, Stale Files, By Category views
- **File Actions**: View details, move, archive, trash, delete
- **Settings Modal**: Configure output directory, AI model, thresholds
- **JSON Export**: Download scan results as JSON

## Usage

### Development

```bash
# Install with web dependencies
pip install -e '.[web]'

# Start the dev server with hot reload
fileforge server --reload
```

### Production

```bash
# Install with web dependencies
pip install '.[web]'

# Start the server (no reload)
fileforge server --host 0.0.0.0 --port 8082
```

Then open http://localhost:8082 in your browser.

## API Endpoints

- `GET /` - Serve index.html
- `GET /api/health` - Health check
- `POST /api/scan` - Start a scan
- `GET /api/stats` - Get current statistics
- `GET /api/sessions` - List all sessions
- `GET /api/session/{id}` - Get session details

## Branding

Follows CoreConduit Brand v2.1:
- Colors: Navy (#0d1b2e), Silver (#d8dde8), Blue (#2b7de9), Orange (#e07018)
- Fonts: Exo 2 (display), Plus Jakarta Sans (body), IBM Plex Mono (code)
- Cards with blue→orange gradient top border
