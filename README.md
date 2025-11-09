# Apple Notes to Notesnook Exporter

Export your Apple Notes to Notesnook markdown format. Extracts notes from the local Apple Notes database with proper protobuf parsing, preserving titles, content, folders, dates, and inline attachments.

## Features

- 📱 Extracts notes directly from Apple Notes SQLite database
- 📝 Exports to Notesnook markdown format with YAML frontmatter
- 🔬 Proper protobuf parsing using Apple Notes schema
- 🏷️ Converts Apple Notes folders to tags
- 📅 Preserves creation and modification dates (ISO 8601)
- 🔗 Resolves inline attachments (hashtags, mentions)
- 🔍 Dry-run mode to preview before exporting
- ✨ Simple CLI interface

## Requirements

- macOS (for Apple Notes access)
- Python 3.9 or higher
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

### After Export

1. Place your attachment files in the `attachments/` subdirectory within the export folder
2. Open Notesnook app
3. Go to Settings > Notesnook Importer
4. Select "Markdown" as the source
5. Select your export folder
6. Review and confirm the import

### Advanced Options

```bash
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

3. **Transform**: Converts to Notesnook markdown format:
   - Title → YAML frontmatter `title` field
   - Content → Markdown body (with inline attachments resolved)
   - Folder → YAML frontmatter `tags` field
   - Created date → YAML frontmatter `created` field (ISO 8601)
   - Modified date → YAML frontmatter `updated` field (ISO 8601)

4. **Export**: Writes markdown files compatible with Notesnook importer

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

- **File attachments**: Images, PDFs, and other file attachments need to be manually placed in the `attachments/` directory
- **Complex formatting**: Tables, drawings, and sketches are not exported (limitations of markdown)
- **macOS only**: Requires access to local Apple Notes database
- **Inline attachments**: Hashtags and mentions are resolved; other inline objects show as `[attachment]`

## Troubleshooting

### "Apple Notes database not found"
- Make sure you're running this on macOS
- Check that Apple Notes app has been opened at least once
- Verify Notes are stored locally (not just in iCloud)

### "Permission denied" on database
- Close Apple Notes app before running the export
- The tool opens the database in read-only mode, but macOS may still lock it

### Notes appear incomplete
- This should not happen with the proper protobuf parser
- If you see `[attachment]` markers, those are embedded objects not yet supported
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
