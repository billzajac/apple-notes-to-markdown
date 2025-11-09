# Apple Notes to Notesnook Exporter

Export your Apple Notes to a markdown format compatible with [Notesnook](https://notesnook.com/). Extracts notes from the local Apple Notes database with proper protobuf parsing, preserving titles, content, folders, dates, and inline attachments.

As of 11/2025, when I tried selecting all notes from Apple Notes to export to markdown, it corrupts the data and leaves out helpful data such as timestamps.

Motivation: I would like a cross-platform solution for my notes. At the time of writing this, getting data into Google Keep has proven to be awkward, and getting data out of Apple Notes has also proven to be awkward.
This tool is to help me export my Apple Notes to Notesnook, which seems like a nice cross-platform notes alternative.

## Features

- 📱 Extracts notes directly from Apple Notes SQLite database
- 📝 Exports to Notesnook markdown format with YAML frontmatter
- 🔬 Proper protobuf parsing using Apple Notes schema
- 🏷️ Converts Apple Notes folders to tags
- 📅 Preserves creation and modification dates (ISO 8601)
- 🔗 Resolves inline attachments (hashtags, mentions)
- 📎 **Extracts file attachments** (images, PDFs, videos) from filesystem
- 🖼️ Auto-generates markdown image/link syntax for attachments
- 🔍 Dry-run mode to preview before exporting
- ✨ Simple CLI interface

## Requirements

- macOS (for Apple Notes access)
- Python 3.9 or higher
- [Homebrew](https://brew.sh/)
- Protocol Buffers compiler (`protoc`) - Install with `brew install protobuf`

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd apple-notes-to-notesnook
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the package:
```bash
pip install -e .
```

4. **Grant Full Disk Access to your Terminal** (Required):

   Since this tool needs to read the Apple Notes database, you must grant Full Disk Access to your terminal application.

   **Option 1: Using System Settings (Recommended)**
   1. Open **System Settings** (or **System Preferences** on older macOS)
   2. Go to **Privacy & Security** → **Full Disk Access**
   3. Click the **+** button to add an application
   4. Navigate to `/Applications/Utilities/` and select your terminal app:
      - **Terminal.app** (built-in Terminal)
      - **iTerm.app** (if using iTerm2)
      - **WezTerm** (if using WezTerm)
      - **Alacritty** (if using Alacritty)
      - Or your preferred terminal application
   5. Toggle the switch to **ON** for your terminal
   6. **Quit and restart your terminal application** for changes to take effect

   **Option 2: Using the CLI Helper**
   ```bash
   # The exporter will detect permission issues and guide you
   notes-export --check-permissions
   ```

   **Important Notes:**
   - You must restart your terminal after granting permissions
   - The tool accesses the database in **read-only mode** and doesn't modify your notes
   - This is a macOS security requirement for accessing user data

The protobuf schema has already been compiled. If you need to recompile:
```bash
protoc --python_out=notes_migrator/ --proto_path=notes_migrator/ notestore.proto
```

## Usage

### Basic Export

```bash
# Activate virtual environment
source venv/bin/activate

# Export all notes to Notesnook markdown format
notes-export

# Export to custom directory
notes-export --output-dir ./my-notes

# Preview what will be exported (dry run)
notes-export --dry-run
```

### Importing to Notesnook

After exporting your notes, you have two options:

**Option 1: Import as ZIP (Recommended)**
```bash
# Zip the export folder
cd /path/to/parent/directory
zip -r my-notes.zip my-notes

# Then in Notesnook:
# Settings → Notesnook Importer → Select 'Markdown' → Choose my-notes.zip
```

**Option 2: Import Folder Directly**
1. Open Notesnook app
2. Go to Settings → Notesnook Importer
3. Select "Markdown" as the source
4. Select your export folder (e.g., `my-notes/`)
5. Review and confirm the import

**✨ What gets imported:**
- All notes with preserved titles, dates, and tags
- File attachments (images, PDFs) automatically included
- Markdown formatting with images embedded as `![](attachments/image.png)`

### Advanced Options

```bash
# Check permissions before exporting
notes-export --check-permissions

# Use custom Apple Notes database path
notes-export --db-path /path/to/NoteStore.sqlite

# Limit number of notes (for testing)
notes-export --max-notes 10

# Custom attachments directory name
notes-export --attachments-dir my-attachments
```

### Get Help

```bash
notes-export --help
```

## How It Works

1. **Extract**: Reads notes from Apple Notes SQLite database at:
   ```
   ~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite
   ```

2. **Parse**: Uses proper protobuf parsing with Apple Notes schema:
   - Decompresses gzipped data (magic bytes: 0x1f 0x8b)
   - Parses `NoteStoreProto.document.note.note_text` field
   - Resolves inline attachments (hashtags, mentions) from database
   - Extracts clean text without junk/metadata

3. **Extract Attachments**: Reads file attachments from filesystem:
   ```
   ~/Library/Group Containers/group.com.apple.notes/Accounts/<UUID>/Media/
   ```
   - Identifies attachments from protobuf `attribute_run` data
   - Reads media files from nested directory structure
   - Preserves original filenames where available

4. **Transform**: Converts to Notesnook markdown format:
   - Title → YAML frontmatter `title` field
   - Content → Markdown body (with inline attachments resolved)
   - Folder → YAML frontmatter `tags` field
   - Created date → YAML frontmatter `created` field (ISO 8601)
   - Modified date → YAML frontmatter `updated` field (ISO 8601)
   - Attachments → Saved to `attachments/` directory
   - `\ufffc` markers → Replaced with `![image](attachments/file.png)` or `[file](attachments/doc.pdf)`

5. **Export**: Writes markdown files compatible with Notesnook importer

## Notesnook Markdown Format

Each note is exported as a `.md` file with YAML frontmatter:

```markdown
---
title: Your Note Title
created: 2024-01-15T10:30:00.000Z
updated: 2024-01-20T15:45:00.000Z
tags: Work
---

Your note content here.

Inline attachments are resolved: #hashtag @mention

Images and attachments: ![description](attachments/image.jpg)
```

## Limitations

- **Complex formatting**: Tables, drawings, and sketches are not exported (limitations of markdown)
- **macOS only**: Requires access to local Apple Notes database
- **Requires Full Disk Access**: Your terminal needs Full Disk Access permission to read Apple Notes data
- **Local notes only**: iCloud-only notes must be synced locally first

## Troubleshooting

### "Apple Notes database not found"
- Make sure you're running this on macOS
- Check that Apple Notes app has been opened at least once
- Verify Notes are stored locally (not just in iCloud)

### "Permission denied" errors
This is the most common issue. The tool needs Full Disk Access to read the Apple Notes database.

**Solution:**
1. Grant Full Disk Access to your terminal (see Installation step 4 above)
2. **Restart your terminal completely** (quit and reopen, not just close the window)
3. Run `notes-export --check-permissions` to verify access
4. If still having issues, try:
   - Removing and re-adding your terminal in Full Disk Access settings
   - Checking that you selected the correct terminal application
   - Running the command from the terminal you granted access to (not a different terminal app)

**Quick permission check:**
```bash
# This will test if you have the necessary permissions
notes-export --check-permissions
```

### Database locked or in use
- Close Apple Notes app before running the export
- The tool opens the database in read-only mode, but macOS may still lock it
- Wait a few seconds after closing Notes and try again

### Attachments not exported
- File attachments (images, PDFs) are automatically extracted and saved to `attachments/`
- Make sure you have read permissions for:
  - `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`
  - `~/Library/Group Containers/group.com.apple.notes/Accounts/*/Media/`
- Grant Full Disk Access to your terminal if attachments are missing

### Notes appear incomplete
- This should not happen with the proper protobuf parser
- If you see remaining `[attachment]` markers, those are unsupported embedded objects (tables, drawings)
- Check the original note in Apple Notes to verify
- Report issues with the protobuf schema

## Security & Privacy

- All processing happens locally on your machine
- No data is sent to external servers
- The tool reads from Apple Notes database in read-only mode
- Exported files are saved to your local filesystem

## Contributing

This is a personal project, but contributions are welcome! Please open an issue or pull request.

## License

MIT License - see LICENSE file for details

## Technical Details

This exporter uses:
- **Apple Notes protobuf schema** - Reverse-engineered schema from [apple-notes-liberator](https://github.com/HamburgChimps/apple-notes-liberator)
- **Forensics research** - Based on [Ciofeca Forensics](https://www.ciofecaforensics.com/categories/#Apple%20Notes) Apple Notes analysis
- **Proper protobuf parsing** - Uses compiled Python protobuf classes, not string extraction
- **Database schema knowledge** - Compatible with iOS 9-18+

## References and Inspiration

This project was made possible by extensive research and open-source contributions:

### Apple Notes Format Research
- [iOS 18 Notes Analysis](https://www.ciofecaforensics.com/2024/12/10/ios18-notes/) - Ciofeca Forensics' latest analysis of Apple Notes structure and iOS 18 changes
- [Apple Notes Protobuf Schema](https://github.com/HamburgChimps/apple-notes-liberator/blob/main/src/main/proto/notestore.proto) - Reverse-engineered protobuf definition
- [apple-notes-liberator](https://github.com/HamburgChimps/apple-notes-liberator) - Ruby-based Apple Notes parser and liberator
- [apple_cloud_notes_parser](https://github.com/threeplanetssoftware/apple_cloud_notes_parser) - Comprehensive Ruby implementation for forensics

### Notesnook Integration
- [Notesnook Markdown Import Documentation](https://help.notesnook.com/importing-notes/import-notes-from-markdown-files#supported-formats) - Official supported formats and import guide
- [Notesnook](https://github.com/streetwriters/notesnook) - Privacy-focused note-taking app

### Migration Guides
- [Migrating from Apple Notes to Google Keep](https://www.mandclu.com/blog/migrating-apple-notes-google-keep) - Background on note migration challenges

## Acknowledgments

Special thanks to:
- **Ciofeca Forensics** for detailed Apple Notes forensics research
- **HamburgChimps** for reverse-engineering the protobuf schema
- **Notesnook team** for building an excellent privacy-focused notes app
- **threeplanetssoftware** for the foundational Ruby parser implementation

## Why Notesnook?

Notesnook is an open-source, privacy-focused note-taking app with:
- End-to-end encryption
- Cross-platform support (Windows, Mac, Linux, iOS, Android, Web)
- Rich markdown support with YAML frontmatter
- No vendor lock-in (notes in standard markdown format)
- Active development and community
