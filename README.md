# Apple Notes to Google Keep Migrator

Migrate your Apple Notes to Google Keep with this Python tool. Extracts notes from the local Apple Notes database and uploads them to Google Keep while preserving titles, content, folders (as labels), and timestamps.

## Features

- 📱 Extracts notes directly from Apple Notes SQLite database
- 📤 Uploads to Google Keep via unofficial API
- 🏷️ Converts Apple Notes folders to Google Keep labels
- 📅 Preserves creation and modification dates
- 🔍 Dry-run mode to preview before migrating
- ✨ Simple CLI interface

## Requirements

- macOS (for Apple Notes access)
- Python 3.9 or higher
- Google account

## Installation

1. Clone this repository:
```bash
cd /Users/billyz/code/apple-notes-to-google-keep
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install the package:
```bash
pip install -e .
```

## Google Account Setup

**Important:** If you have 2-factor authentication enabled (recommended), you'll need to create an app-specific password:

1. Go to https://myaccount.google.com/apppasswords
2. Select "Mail" and "Mac" (or "Other")
3. Generate password
4. Use this password instead of your regular password

## Usage

### Basic migration (recommended to try dry-run first):

```bash
# Preview what will be migrated without actually doing it
notes-migrate --dry-run

# Migrate all notes
notes-migrate
```

### Advanced options:

```bash
# Use custom Apple Notes database path
notes-migrate --db-path /path/to/NoteStore.sqlite

# Use custom label for migrated notes
notes-migrate --label "Imported from Mac"

# Limit number of notes (for testing)
notes-migrate --max-notes 5

# Provide username upfront
notes-migrate --username your-email@gmail.com
```

### Get help:

```bash
notes-migrate --help
```

## How It Works

1. **Extract**: Reads notes from Apple Notes SQLite database at:
   ```
   ~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite
   ```

2. **Transform**: Converts Apple Notes data structure to Google Keep format:
   - Title → Note title
   - Content → Note content
   - Folder → Label
   - Timestamps → Creation/modification dates

3. **Load**: Uploads notes to Google Keep using the `gkeepapi` library

## Limitations

- **Text only**: Attachments, images, sketches, and complex formatting are not supported
- **Unofficial API**: Uses unofficial Google Keep API which may break with Google updates
- **Rate limiting**: Large migrations may be slow to avoid API rate limits
- **macOS only**: Requires access to local Apple Notes database

## Troubleshooting

### "Apple Notes database not found"
- Make sure you're running this on macOS
- Check that Apple Notes app has been opened at least once
- Verify Notes are stored locally (not just in iCloud)

### "Failed to login to Google Keep"
- Use app-specific password if you have 2FA enabled
- Check your username/email is correct
- Ensure you have access to Google Keep (some workspace accounts restrict it)

### "Permission denied" on database
- Close Apple Notes app before running the migration
- The tool opens the database in read-only mode, but macOS may still lock it

### Notes appear empty or garbled
- Apple Notes content extraction is complex; some formatting may be lost
- Check the original note in Apple Notes to verify content exists
- Try exporting a test note first with `--max-notes 1`

## Security & Privacy

- Your Google credentials are only used to authenticate with Google Keep
- No credentials are stored (except optionally in system keyring via gkeepapi)
- All processing happens locally on your machine
- The tool reads from Apple Notes database in read-only mode

## Contributing

This is a personal project, but contributions are welcome! Please open an issue or pull request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [gkeepapi](https://github.com/kiwiz/gkeepapi) - Unofficial Google Keep API client
- Inspired by [NotesMigrator](https://github.com/mgks/NotesMigrator)

## Disclaimer

This tool uses an unofficial Google Keep API. Use at your own risk. Always backup your notes before migration.
