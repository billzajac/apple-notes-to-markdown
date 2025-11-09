# Notesnook Markdown Import Format - Research Findings

## 1. Supported Markdown Formats

Notesnook's markdown importer supports:

- **100% CommonMark syntax** - standard markdown
- **GitHub Flavored Markdown (GFM)** - task lists, tables, strikethrough
- **Obsidian Flavored Markdown** - embedded files, comments
- **Math equations** - inline ($...$) and block ($$...$$)
- **Superscript and subscript** - `19^th^` and `H~2~O`
- **Highlights** - `==highlighted text==` renders with yellow background
- **Code blocks with language syntax highlighting** - ` ```language\ncode\n``` `
- **Wiki-style embedded files** - `![[image.jpg]]` and `![[image.jpg|100x100]]`
- **Comments** - Obsidian-style `%%comment%%` (inline or block)

## 2. YAML Frontmatter Format

Notesnook uses **YAML frontmatter** (delimited by `---`) for metadata. Frontmatter must be at the beginning of the file.

### Supported Frontmatter Fields

```yaml
---
title: Note Title
tags: tag1,tag2  # Can be comma-separated string OR array: [tag1, tag2]
pinned: true/false
favorite: true/false

# Date fields (multiple variations supported)
created: 2013-06-06T09:00:00.001Z
created_at: 2013-06-06T09:00:00.001Z
created-at: 2013-06-06T09:00:00.001Z
date created: 2013-06-06T09:00:00.001Z

updated: 2014-05-16T10:30:00.001Z
updated_at: 2014-05-16T10:30:00.001Z
updated-at: 2014-05-16T10:30:00.001Z
date updated: 2014-05-16T10:30:00.001Z

# Alternative date field names (also supported but not recommended)
edited: 2014-05-16T10:30:00.001Z
edited_at: 2014-05-16T10:30:00.001Z
edited-at: 2014-05-16T10:30:00.001Z
date edited: 2014-05-16T10:30:00.001Z

color: blue  # Color string (see supported colors below)
---
```

### Supported Color Values
From importer code at `/tmp/notesnook/apps/web/src/utils/importer.ts`:
- teal → `#00897B`
- red → `#D32F2F`
- purple → `#7B1FA2`
- blue → `#1976D2`
- cerulean → `#03A9F4`
- pink → `#C2185B`
- brown → `#795548`
- gray → `#9E9E9E`
- green → `#388E3C`
- orange → `#FFA000`
- yellow → `#FFC107`

### Tag Field Handling
- Tags can be comma-separated string: `tags: wonderful,journal`
- Tags can be an array: `tags: [wonderful, journal]`
- Frontmatter parser automatically strips `#` prefix if present: `tags: "#tag1,#tag2"` → `["tag1", "tag2"]`
- Tags are trimmed of whitespace

### Date Parsing
- All date formats support ISO 8601 strings
- Parser uses `new Date(dateString).getTime()` for conversion
- Fallback order for date fields in code:
  - For created dates: `created` → `created_at` → `date created`
  - For updated dates: `updated` → `updated_at` → `date updated`

## 3. Metadata Handling Without Frontmatter

If no frontmatter is present:
- **Title**: Uses first H1/H2 header found, or filename if no header exists
- **Created/Modified dates**: Falls back to file's actual timestamps
- **Tags, color, pinned, favorite**: Not set (defaults)

## 4. Attachment/Image Handling

### Image References in Markdown

**Standard Markdown Images:**
```markdown
![Alt text](path/to/image.jpg)
![Stormtroopocat](image.jpg "The Stormtroopocat")
```

**Wiki-style Embedded Files (Obsidian format):**
```markdown
![[image.jpg]]                    # Simple embed
![[image.jpg|100]]                # With width
![[image.jpg|100x100]]            # With width and height
![[image.pdf#section]]            # With hash/anchor (hash ignored)
![[image.pdf|IMAGE_ALIAS]]        # With alias (alias ignored)
```

### Attachment Processing

Key details from `HTML.ts` processHTML method:
1. **File Resolution**: Links to local files get converted to attachments if the file exists in the import set
   - Parser looks for files matching the path relative to the markdown file's directory
   - Supports both `src` (images) and `href` (links) attributes

2. **Attachment Metadata**:
   ```typescript
   {
     filename: string,          // Original filename
     size: number,              // File size in bytes
     hash: string,              // xxh64 hash
     hashType: "xxh64",         // Hash algorithm
     mime: string,              // MIME type (auto-detected)
     data: Uint8Array          // File binary data
   }
   ```

3. **MIME Type Detection**:
   - Auto-detects from file content
   - Falls back to extension-based mapping:
     - `.jpg`, `.jpeg` → `image/jpeg`
     - `.png` → `image/png`
     - `.webp` → `image/webp`
     - `.gif` → `image/gif`
     - `.pdf` → `application/pdf`
     - etc.

4. **ZIP Archive Support**: 
   - Recommended to ZIP all markdown files with attachments
   - Importer extracts ZIP and resolves relative paths within it
   - Per documentation: "For best results, it is recommended to ZIP all your .md files and their attachments so they can be found by the importer."

### Attachment in HTML Output

Attachments are rendered as HTML spans in the note content:
```html
<span class="attachment" 
      data-filename="file.pdf" 
      data-size="4.8K" 
      data-hash="b0dd3ba85df878c2" 
      data-mime="application/pdf"
      title="file.pdf">
  <em>&nbsp;</em>
  <span class="filename">file.pdf</span>
</span>
```

## 5. File Extensions Supported

- `.md`
- `.markdown`
- `.mdown`

## 6. Complete Example

**Example markdown file with frontmatter:**

```markdown
---
title: A beautiful morning
tags: wonderful,journal
pinned: true
favorite: true
created_at: 2013-06-06T09:00:00.001Z
updated_at: 2014-05-16T10:30:00.001Z
color: blue
---

# An h1 header

Paragraphs are separated by a blank line.

2nd paragraph. _Italic_, **bold**, and `monospace`. Itemized lists
look like:

- this one
- that one
- the other one

## An h2 header

Here's a numbered list:

1.  first item
2.  second item
3.  third item

### Markdown Features Example

Subscript and superscript:
- 19^th^
- H~2~O

Highlights:
I am ==highlighted== **again**.

Code blocks with language:
```python
import time
for i in range(10):
    time.sleep(0.5)
    print(i)
```

Task lists (GFM):
- [ ] Task item 1
- [x] Task item 2

Tables (GFM):
| Option | Description |
| ------ | ----------- |
| data   | path to data files |
| engine | engine to be used |

Math equations:
Inline: $2+2=4$

Block:
$$
L = \frac{1}{2} \rho v^2 S C_L
$$

Images:
![Example image](example-image.jpg "An exemplary image")

Wiki-style embeds:
![[image.jpg|100x100]]

Obsidian comments:
This is visible %%this comment is hidden%% text.

And links:
[link text](http://example.com)
```

## 7. Code References

### Markdown Provider Implementation
- **File**: `/tmp/notesnook-importer/packages/core/src/providers/md/index.ts`
- **Class**: `Markdown implements IFileProvider<MarkdownSettings>`
- **Process flow**:
  1. Read markdown file text
  2. Parse frontmatter using `parseFrontmatter()`
  3. Convert markdown to HTML using `markdowntoHTML()`
  4. Process HTML for attachments using `HTML.processHTML()`
  5. Apply frontmatter metadata to note object

### Frontmatter Parser
- **File**: `/tmp/notesnook-importer/packages/core/src/utils/frontmatter.ts`
- Uses: `gray-matter` library for YAML parsing
- Returns: `{ frontmatter?: {...}, content: string }`

### Markdown to HTML Converter
- **File**: `/tmp/notesnook-importer/packages/core/src/utils/to-html.ts`
- Uses: `remark` + `rehype` pipeline with plugins:
  - `remark-gfm` - GitHub Flavored Markdown
  - `remark-math` - Math equations
  - `remark-supersub` - Superscript/subscript
  - Custom plugins for highlights, comments, and file embeds

### HTML Processor
- **File**: `/tmp/notesnook-importer/packages/core/src/providers/html/index.ts`
- Extracts and processes attachments from HTML
- Resolves local file references
- Generates MIME types
- Creates Notesnook-compatible attachment objects

## 8. Output Format

Notes are converted to Notesnook's internal JSON format:

```json
{
  "title": "Note Title",
  "dateCreated": 1370529600001,      // Unix timestamp in milliseconds
  "dateEdited": 1400213400001,       // Unix timestamp in milliseconds
  "pinned": true,
  "favorite": true,
  "color": "blue",
  "tags": ["wonderful", "journal"],
  "content": {
    "type": "tiptap",                // Always tiptap (HTML-based editor format)
    "data": "<p>HTML content here</p>"
  },
  "attachments": [
    {
      "filename": "example-image.jpg",
      "size": 12345,
      "hash": "xxh64hashvalue",
      "hashType": "xxh64",
      "mime": "image/jpeg",
      "data": <Uint8Array>            // Binary file data
    }
  ],
  "notebooks": [                      // Notebook hierarchy
    {
      "title": "Notebook Name",
      "children": []
    }
  ]
}
```

## 9. Important Notes for Integration

1. **No Frontmatter Required**: Files without frontmatter still import successfully - title comes from first heading or filename
2. **Flexible Date Fields**: Support multiple field name variations for compatibility with different markdown note apps
3. **Tag Flexibility**: Tags can be comma-separated or arrays, with optional `#` prefix
4. **Attachment Resolution**: Local file paths must be resolvable - recommended to provide files in ZIP with consistent relative paths
5. **Content Type**: Markdown is converted to HTML (`tiptap` format) before importing, not stored as markdown
6. **Color Support**: Only specific color names are supported (not arbitrary hex codes in frontmatter, though hex codes map internally)
7. **Comment Removal**: Obsidian-style `%%...%%` comments are stripped during conversion, not preserved

## 10. Test Data Location

- **Test fixtures**: `/tmp/notesnook-importer/packages/core/__tests__/data/md/`
  - `md-with-frontmatter.md` - Example with full metadata
  - `test.md` - Example without frontmatter
  - `test2.md` - Additional test case

- **Expected outputs**: `/tmp/notesnook-importer/packages/core/__tests__/__snapshots__/md.snapshot.json`

