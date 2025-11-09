# Apple Notes to Notesnook Exporter - Development Status

**Last Updated**: November 9, 2024
**Status**: Fully Functional (Attachment Extraction Pending)

---

## Current State

The project is **fully functional** for exporting Apple Notes text content to Notesnook markdown format. The implementation uses proper protobuf parsing with the Apple Notes schema for clean, accurate extraction.

### ✅ Completed Features

1. **Proper Protobuf Parsing**
   - Uses compiled `notestore.proto` schema from apple-notes-liberator
   - Parses `NoteStoreProto.document.note.note_text` field directly
   - No junk/metadata extraction - clean text only
   - Handles gzipped data (magic bytes: 0x1f 0x8b)

2. **Inline Attachment Resolution**
   - Resolves hashtags from `com.apple.notes.inlinetextattachment.hashtag` type
   - Resolves mentions from mention-type attachments
   - Queries database for `ZALTTEXT` field to get actual text
   - Replaces `\ufffc` (U+FFFC) markers with resolved content

3. **Notesnook Export Format**
   - YAML frontmatter with `title`, `created`, `updated`, `tags`
   - ISO 8601 date formatting
   - Character encoding cleanup (removes â, Â, ï¿¼ artifacts)
   - Markdown body with clean text

4. **CLI Interface**
   - Command: `notes-export`
   - Simplified interface (removed all Google Keep code)
   - Default output: `./my-notes/`
   - Dry-run support for preview

5. **Database Schema Knowledge**
   - Compatible with iOS 9-18+
   - Understands table structure: ZICCLOUDSYNCINGOBJECT, ZICNOTEDATA, etc.
   - Read-only database access

---

## 🚧 Next Feature: Attachment Extraction

### Goal
Extract file attachments (images, PDFs, etc.) from Apple Notes database and save them to the `attachments/` directory with proper markdown references.

### Current Limitation
- Inline attachments (hashtags, mentions) ✅ Working
- File attachments (images, PDFs, videos) ❌ Not implemented
- Notes show `[attachment]` placeholder where files should be

### Implementation Plan

#### 1. Update AppleNote Dataclass
Location: `notes_migrator/apple_notes.py`

```python
@dataclass
class AppleNote:
    """Represents a note extracted from Apple Notes."""
    title: str
    content: str
    created_date: Optional[datetime]
    modified_date: Optional[datetime]
    folder: Optional[str]
    attachments: List[Dict[str, Any]] = field(default_factory=list)  # ADD THIS
```

Each attachment dict should contain:
```python
{
    'uuid': str,           # Attachment UUID
    'type_uti': str,       # com.apple.image, public.jpeg, etc.
    'filename': str,       # Original or generated filename
    'data': bytes,         # Binary file data
    'position': int,       # Character position in note_text where \ufffc appears
}
```

#### 2. Add Attachment Extraction Method
Location: `notes_migrator/apple_notes.py` in `AppleNotesExtractor` class

```python
def _extract_attachments(self, note_pk: int, attribute_runs) -> List[Dict[str, Any]]:
    """Extract file attachments for a note.

    Args:
        note_pk: Primary key of the note in ZICCLOUDSYNCINGOBJECT
        attribute_runs: List of AttributeRun from protobuf

    Returns:
        List of attachment dictionaries with file data
    """
    attachments = []
    pos = 0

    for attr_run in attribute_runs:
        if attr_run.HasField('attachment_info'):
            attachment_id = attr_run.attachment_info.attachment_identifier
            type_uti = attr_run.attachment_info.type_uti

            # Skip inline attachments (already handled)
            if 'hashtag' in type_uti or 'mention' in type_uti:
                pos += attr_run.length
                continue

            # Get attachment data from database
            cursor = self.conn.cursor()

            # Query for file attachments
            cursor.execute("""
                SELECT
                    ZIDENTIFIER,
                    ZTYPEUTI,
                    ZFILENAME,
                    ZMEDIA.ZDATA as media_data,
                    ZMEDIA.ZFILENAME as media_filename
                FROM ZICCLOUDSYNCINGOBJECT
                LEFT JOIN ZMEDIA ON ZICCLOUDSYNCINGOBJECT.ZMEDIA = ZMEDIA.Z_PK
                WHERE ZIDENTIFIER = ?
            """, (attachment_id,))

            row = cursor.fetchone()
            if row:
                uuid, uti, filename, data, media_filename = row

                # Determine filename
                final_filename = filename or media_filename or f"{uuid[:8]}.bin"

                if data:
                    attachments.append({
                        'uuid': uuid,
                        'type_uti': uti or type_uti,
                        'filename': final_filename,
                        'data': data,
                        'position': pos
                    })

        pos += attr_run.length

    return attachments
```

#### 3. Update Note Extraction
Location: `notes_migrator/apple_notes.py` in `extract_all_notes()` method

Find the loop that creates `AppleNote` objects and add:

```python
for row in rows:
    pk, title, snippet, created, modified, folder, content_data = row

    # Extract text content from binary data
    content = self._extract_content(content_data, snippet)

    # NEW: Extract attachments
    attachments = []
    if content_data:
        try:
            decompressed = gzip.decompress(content_data) if is_gzipped(content_data) else content_data
            note_store = notestore_pb2.NoteStoreProto()
            note_store.ParseFromString(decompressed)
            if note_store.HasField('document') and note_store.document.HasField('note'):
                attachments = self._extract_attachments(pk, note_store.document.note.attribute_run)
        except:
            pass

    # Convert Apple's time format
    created_date = self._convert_apple_timestamp(created)
    modified_date = self._convert_apple_timestamp(modified)

    note = AppleNote(
        title=title or "Untitled",
        content=content,
        created_date=created_date,
        modified_date=modified_date,
        folder=folder,
        attachments=attachments  # ADD THIS
    )
    notes.append(note)
```

#### 4. Update NotesnookExporter
Location: `notes_migrator/notesnook_export.py`

Add method to save attachments:

```python
def _save_attachments(self, note: AppleNote, output_dir: Path, attachments_dir: str) -> Dict[int, str]:
    """Save note attachments to disk.

    Args:
        note: AppleNote with attachments
        output_dir: Base output directory
        attachments_dir: Attachments subdirectory name

    Returns:
        Dict mapping position to relative filename
    """
    attachments_path = output_dir / attachments_dir
    attachments_path.mkdir(exist_ok=True)

    position_to_file = {}

    for i, attachment in enumerate(note.attachments):
        # Generate unique filename
        base_name = Path(attachment['filename']).stem
        extension = Path(attachment['filename']).suffix

        # Ensure uniqueness
        counter = 0
        filename = attachment['filename']
        while (attachments_path / filename).exists():
            counter += 1
            filename = f"{base_name}_{counter}{extension}"

        # Write file
        file_path = attachments_path / filename
        file_path.write_bytes(attachment['data'])

        # Map position to relative path
        position_to_file[attachment['position']] = f"{attachments_dir}/{filename}"

        print(f"  💾 Saved attachment: {filename}")

    return position_to_file
```

Update `_write_markdown()` method:

```python
def _write_markdown(self, note: AppleNote, path: Path, attachments_dir: str) -> None:
    """Write note as markdown file with YAML frontmatter."""

    # ... existing frontmatter code ...

    # Build content
    content = note.content or ""

    # Save attachments and get position mapping
    position_to_file = self._save_attachments(note, path.parent, attachments_dir)

    # Replace \ufffc markers with markdown image/link syntax
    if position_to_file:
        content = self._replace_attachment_markers(content, position_to_file)

    # Process content for other attachments
    content = self._process_content_for_attachments(content, attachments_dir)

    # Clean up problematic characters
    content = self._clean_content(content)

    # Combine frontmatter and content
    markdown = "\n".join(frontmatter) + "\n\n" + content

    path.write_text(markdown, encoding='utf-8')
```

Add helper method:

```python
def _replace_attachment_markers(self, text: str, position_to_file: Dict[int, str]) -> str:
    """Replace \ufffc markers with markdown references.

    Args:
        text: Note text with markers
        position_to_file: Mapping of character position to file path

    Returns:
        Text with markdown image/link syntax
    """
    result = []
    for i, char in enumerate(text):
        if char == '\ufffc' and i in position_to_file:
            file_path = position_to_file[i]
            # Determine if it's an image based on extension
            ext = Path(file_path).suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic']:
                result.append(f"![attachment]({file_path})")
            else:
                # For other files, use link syntax
                filename = Path(file_path).name
                result.append(f"[{filename}]({file_path})")
        elif char != '\ufffc':
            result.append(char)

    return ''.join(result)
```

---

## Database Schema Reference

### Key Tables for Attachments

**ZICCLOUDSYNCINGOBJECT**
- `Z_PK` - Primary key
- `ZIDENTIFIER` - UUID of object
- `ZTYPEUTI` - Type identifier
- `ZFILENAME` - Filename (may be NULL)
- `ZMEDIA` - Foreign key to ZMEDIA table

**ZMEDIA**
- `Z_PK` - Primary key
- `ZDATA` - Binary file data (may be gzipped)
- `ZFILENAME` - Filename
- `ZHEIGHT`, `ZWIDTH` - For images
- `ZDURATION` - For videos/audio

**Attachment Type UTIs**
- `com.apple.image` - Generic image
- `public.jpeg`, `public.png` - Specific image formats
- `com.adobe.pdf` - PDF files
- `public.movie` - Video files
- `com.apple.notes.inlinetextattachment.hashtag` - Hashtag (already handled)
- `com.apple.notes.inlinetextattachment.mention` - Mention (already handled)

---

## Testing Strategy

1. **Test with image attachment**
   ```bash
   notes-export --max-notes 1 --output-dir ./test-images
   # Verify image file saved and markdown references it
   ```

2. **Test with PDF attachment**
   ```bash
   notes-export --max-notes 1 --output-dir ./test-pdfs
   ```

3. **Test with multiple attachments**
   ```bash
   notes-export --max-notes 1 --output-dir ./test-multi
   ```

4. **Verify in Notesnook**
   - Import the exported folder
   - Check that images display inline
   - Check that PDF links work

---

## File Structure

```
notes_migrator/
├── __init__.py
├── apple_notes.py          # Main extraction logic - ADD ATTACHMENT METHODS HERE
├── cli.py                  # CLI interface (no changes needed)
├── notesnook_export.py     # Export to markdown - ADD ATTACHMENT SAVING HERE
├── notestore_pb2.py        # Generated protobuf (don't modify)
└── notestore.proto         # Protobuf schema (don't modify)
```

---

## Known Issues & Edge Cases

1. **Encrypted Notes**: Not supported (requires password)
2. **iCloud-only Notes**: Must be synced locally first
3. **Large Attachments**: May hit memory limits (consider streaming)
4. **Duplicate Filenames**: Handled with counter suffix
5. **Unsupported Types**: Tables, drawings - will show as `[attachment]`

---

## Resources

- [Apple Notes Liberator](https://github.com/HamburgChimps/apple-notes-liberator) - Protobuf schema source
- [iOS 18 Notes Analysis](https://www.ciofecaforensics.com/2024/12/10/ios18-notes/) - Latest structure
- [Notesnook Import Docs](https://help.notesnook.com/importing-notes/import-notes-from-markdown-files#supported-formats)

---

## Quick Start for Continuation

1. **Read current code**:
   ```bash
   cat notes_migrator/apple_notes.py | grep -A 20 "class AppleNote"
   cat notes_migrator/apple_notes.py | grep -A 50 "def extract_all_notes"
   ```

2. **Test current functionality**:
   ```bash
   notes-export --max-notes 2 --output-dir ./test
   cat test/*.md
   ```

3. **Implement attachment extraction** following the plan above

4. **Test thoroughly** with notes containing images, PDFs, and mixed content

---

## Contact & Notes

- Package name: `apple-notes-to-notesnook`
- CLI command: `notes-export`
- Default output: `./my-notes/`
- Python version: 3.9+
- Main dependency: `protobuf>=4.21.0`

**Current Status**: Text extraction is production-ready. Attachment extraction is next priority feature.
