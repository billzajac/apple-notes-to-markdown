# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Apple Notes to Notesnook exporter - extracts notes from Apple's Notes.app SQLite database and exports them to Notesnook-compatible markdown format with YAML frontmatter.

**Current Status**: Planning phase - implementation not yet started. See DEVELOPMENT_STATUS.md for detailed implementation plan.

## Architecture Plan

### Core Components

1. **`notes_migrator/apple_notes.py`** - Apple Notes extraction
   - Uses compiled protobuf schema (`notestore_pb2.py`) from apple-notes-liberator
   - Reads from `~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`
   - Parses `NoteStoreProto.document.note.note_text` field from gzipped protobuf data
   - Handles inline attachments (hashtags, mentions) by resolving `\ufffc` markers
   - Future: Extract file attachments (images, PDFs) from ZMEDIA table

2. **`notes_migrator/notesnook_export.py`** - Notesnook format exporter
   - Generates markdown files with YAML frontmatter
   - Frontmatter fields: `title`, `created`, `updated`, `tags`
   - ISO 8601 date formatting
   - Character encoding cleanup (removes â, Â, ï¿¼ artifacts)
   - Future: Save attachments to `attachments/` subdirectory with markdown references

3. **`notes_migrator/cli.py`** - Command-line interface
   - Command: `notes-export`
   - Default output: `./my-notes/`
   - Supports `--dry-run`, `--max-notes`, `--output-dir` flags

4. **`notes_migrator/notestore.proto` + `notestore_pb2.py`** - Protobuf schema
   - Schema from apple-notes-liberator project
   - Don't modify generated `notestore_pb2.py`
   - Recompile with: `protoc --python_out=. notestore.proto`

### Data Models

**AppleNote dataclass** (`notes_migrator/apple_notes.py`):
```python
@dataclass
class AppleNote:
    title: str
    content: str
    created_date: Optional[datetime]
    modified_date: Optional[datetime]
    folder: Optional[str]
    attachments: List[Dict[str, Any]]  # Planned for file attachments
```

### Database Schema

**Apple Notes SQLite** (`~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite`):

Key tables:
- `ZICCLOUDSYNCINGOBJECT` - Main objects table (notes, folders, attachments)
  - `Z_PK` - Primary key
  - `ZIDENTIFIER` - UUID
  - `ZTYPEUTI` - Type identifier
  - `ZNOTE` - Foreign key to note
  - `ZMEDIA` - Foreign key to media table

- `ZICNOTEDATA` - Note content (protobuf binary)
  - `ZDATA` - Gzipped protobuf data (check magic bytes: 0x1f 0x8b)
  - `ZNOTE` - Foreign key to parent note

- `ZMEDIA` - File attachments (images, PDFs)
  - `ZDATA` - Binary file data (may be gzipped)
  - `ZFILENAME` - Original filename
  - `ZHEIGHT`, `ZWIDTH` - Image dimensions

**Inline Attachment Resolution**:
- Text contains `\ufffc` (U+FFFC) object replacement character markers
- Protobuf `attribute_run` array maps positions to attachment identifiers
- Query `ZALTTEXT` field to resolve hashtag/mention text
- File attachments (images, PDFs) need ZMEDIA table join

## Key Technical Details

### Protobuf Parsing
- Note content stored as gzipped protobuf in `ZICNOTEDATA.ZDATA`
- Check for gzip magic bytes (0x1f 0x8b) before decompression
- Parse with: `notestore_pb2.NoteStoreProto()`
- Access text via: `note_store.document.note.note_text`

### Timestamp Conversion
- Apple uses Core Data timestamps: seconds since 2001-01-01 00:00:00 UTC
- Convert to datetime: `datetime(2001, 1, 1) + timedelta(seconds=timestamp)`

### Character Encoding Issues
- Remove: `â`, `Â`, `ï¿¼` (common encoding artifacts)
- Replace `\ufffc` with resolved attachment content or markdown references

### Attachment Type UTIs
- `com.apple.notes.inlinetextattachment.hashtag` - Hashtag (inline)
- `com.apple.notes.inlinetextattachment.mention` - Mention (inline)
- `com.apple.image`, `public.jpeg`, `public.png` - Images (file)
- `com.adobe.pdf` - PDF files (file)
- `public.movie` - Videos (file)

## Development Workflow

### Package Setup (Not Yet Implemented)
```bash
# Install in development mode
pip install -e .

# Run CLI
notes-export --output-dir ./test-export --dry-run
```

### Testing Strategy
1. Test with notes containing only text
2. Test with notes containing hashtags/mentions
3. Test with notes containing images
4. Test with notes containing PDFs
5. Test with notes containing multiple attachments
6. Verify import into Notesnook app

### Common Database Queries

**Get all notes**:
```sql
SELECT
    obj.Z_PK,
    obj.ZTITLE1,
    obj.ZSNIPPET,
    obj.ZCREATIONDATE,
    obj.ZMODIFICATIONDATE,
    folder.ZTITLE2 as folder_name,
    data.ZDATA
FROM ZICCLOUDSYNCINGOBJECT obj
LEFT JOIN ZICNOTEDATA data ON obj.ZNOTEDATA = data.Z_PK
LEFT JOIN ZICCLOUDSYNCINGOBJECT folder ON obj.ZFOLDER = folder.Z_PK
WHERE obj.ZTITLE1 IS NOT NULL
  AND obj.ZMARKEDFORDELETION = 0
```

**Resolve inline attachment**:
```sql
SELECT ZALTTEXT
FROM ZICCLOUDSYNCINGOBJECT
WHERE ZIDENTIFIER = ?
```

**Get file attachment**:
```sql
SELECT
    ZIDENTIFIER,
    ZTYPEUTI,
    ZFILENAME,
    ZMEDIA.ZDATA as media_data,
    ZMEDIA.ZFILENAME as media_filename
FROM ZICCLOUDSYNCINGOBJECT
LEFT JOIN ZMEDIA ON ZICCLOUDSYNCINGOBJECT.ZMEDIA = ZMEDIA.Z_PK
WHERE ZIDENTIFIER = ?
```

## Known Limitations

- Encrypted notes not supported (requires password)
- iCloud-only notes must be synced locally first
- Tables and drawings not supported (show as `[attachment]`)
- Compatible with iOS 9-18+ schema

## Implementation Status

**See DEVELOPMENT_STATUS.md for**:
- Detailed implementation plan for attachment extraction
- Step-by-step code examples with exact locations
- Database schema reference
- Testing strategy

Current phase: Project setup and core text extraction (not yet implemented)
Next phase: Implement attachment extraction
