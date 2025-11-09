# Notesnook Import Format - Research Summary

Research Date: 2025-11-08
Source: Analysis of https://github.com/streetwriters/notesnook and https://github.com/streetwriters/notesnook-importer

## TL;DR - What Notesnook Expects

Notesnook imports markdown files with YAML frontmatter metadata:

```markdown
---
title: My Note Title
tags: tag1, tag2
created_at: 2023-06-06T09:00:00.000Z
updated_at: 2023-06-16T10:30:00.000Z
pinned: true
favorite: false
color: blue
---

# Your markdown content here

Standard markdown, **bold**, *italic*, `code`, etc.

- Supports task lists with [ ] and [x]
- GitHub flavored markdown (tables, strikethrough)
- Math: $inline$ and $$display$$
- Superscript: 19^th^ and Subscript: H~2~O
- Highlights: ==yellow background==
- Images: ![alt](attachments/image.jpg)
```

## Key Format Details

### Frontmatter Metadata
- **Required**: None (all fields optional)
- **YAML format**: Delimited by `---` at file start
- **Supported fields**:
  - `title` - Note title (string)
  - `tags` - Comma-separated string OR array
  - `pinned` - Boolean (true/false)
  - `favorite` - Boolean (true/false)
  - `color` - One of: blue, red, green, orange, yellow, purple, pink, teal, cerulean, brown, gray
  - `created`/`created_at`/`created-at`/`date created` - ISO 8601 date
  - `updated`/`updated_at`/`updated-at`/`date updated` - ISO 8601 date

### Markdown Support
- CommonMark 100%
- GitHub Flavored Markdown (GFM) - tables, checklists, strikethrough
- Obsidian format - wiki-style `![[file]]` embeds, `%%comment%%` syntax
- Math equations - `$...$` inline, `$$...$$` block
- Superscript/subscript - `19^th^`, `H~2~O`
- Highlights - `==text==` (yellow)
- Code blocks with syntax highlighting

### Attachments/Images
- Referenced via relative paths: `![alt](attachments/image.jpg)`
- Wiki-style: `![[image.jpg|100x100]]`
- Files must exist in import set
- Recommended: ZIP all markdown + attachments together
- Auto-detects MIME types from file content

### File Extensions
- `.md`
- `.markdown`
- `.mdown`

## Processing Pipeline

1. **Parse**: Extract YAML frontmatter using `gray-matter` library
2. **Convert**: Transform markdown to HTML using `remark` + `rehype`
3. **Attach**: Resolve image/file references and create attachments
4. **Metadata**: Apply frontmatter fields to note object
5. **Import**: Store in Notesnook database with encryption

## Implementation Notes

1. **Frontmatter is optional** - Files without it still work (title from first H1/H2 or filename)

2. **Date field flexibility** - Multiple field name variants supported:
   - `created`, `created_at`, `created-at`, `date created`
   - `updated`, `updated_at`, `updated-at`, `date updated`
   - Parser tries each in order until found

3. **Tag flexibility** - Both formats work:
   - `tags: wonderful, journal` (comma-separated)
   - `tags: [wonderful, journal]` (YAML array)
   - `#` prefix automatically stripped

4. **Content conversion** - Markdown converted to HTML internally (not stored as markdown)

5. **Color limitation** - Only 11 colors supported (no arbitrary hex in frontmatter)

6. **Attachment handling** - Files must be resolvable via relative paths

7. **Comment preservation** - Obsidian-style `%%comments%%` are REMOVED, not preserved

8. **Directory structure** - No automatic notebook creation from directory hierarchy

## Critical Implementation Details

### Date Handling
- Accept ISO 8601 format in frontmatter
- Parser converts to millisecond Unix timestamps internally
- Example: `2023-06-06T09:00:00.000Z`

### Tag Processing
```python
# Input: "wonderful, journal" or ["wonderful", "journal"]
# Output: ["wonderful", "journal"]
# Also strips leading # if present
```

### Color Mapping (from importer code)
```
teal      → #00897B
red       → #D32F2F
purple    → #7B1FA2
blue      → #1976D2
cerulean  → #03A9F4
pink      → #C2185B
brown     → #795548
gray      → #9E9E9E
green     → #388E3C
orange    → #FFA000
yellow    → #FFC107
```

### Markdown to HTML Transformations
```
==text==           → <span style="background-color: rgb(255, 255, 0);">text</span>
19^th^             → 19<sup>th</sup>
H~2~O              → H<sub>2</sub>O
$formula$          → <span class="math math-inline">formula</span>
$$formula$$        → <div class="math math-display">formula</div>
- [ ] Task         → <li class="checklist--item">Task</li>
- [x] Completed    → <li class="checklist--item checked">Completed</li>
![[image.jpg]]     → <a href="image.jpg"></a>
![[image.jpg|100]] → <a href="image.jpg" width="100"></a>
%%comment%%        → [REMOVED]
```

## Validation Checklist

Before exporting to Notesnook:
- [ ] All markdown files have correct extension (`.md`, `.markdown`, or `.mdown`)
- [ ] YAML frontmatter is at the beginning (if included)
- [ ] All dates are ISO 8601 format
- [ ] All image references have valid relative paths
- [ ] Attachment files exist at referenced paths
- [ ] Color values are from the supported list
- [ ] Tag names don't have special characters (except trimmed spaces removed)
- [ ] Frontmatter YAML has no unescaped special characters
- [ ] All files are UTF-8 encoded

## Documentation Structure

Three comprehensive guides created:

1. **NOTESNOOK_IMPORT_FORMAT.md** (327 lines)
   - Detailed format specification
   - All supported markdown features
   - Complete frontmatter reference
   - Attachment handling details
   - Output format specification

2. **NOTESNOOK_IMPLEMENTATION_GUIDE.md** (260 lines)
   - TypeScript implementation templates
   - Export function examples
   - Helper functions for formatting
   - Validation checklist
   - Testing recommendations

3. **NOTESNOOK_CODE_REFERENCE.md** (517 lines)
   - Complete source code from Notesnook
   - Markdown provider implementation
   - Frontmatter parser details
   - HTML conversion pipeline
   - Attachment processing logic
   - Web importer integration code

## Source Files Referenced

From https://github.com/streetwriters/notesnook-importer:
- `packages/core/src/providers/md/index.ts` - Markdown provider
- `packages/core/src/utils/frontmatter.ts` - YAML parser
- `packages/core/src/utils/to-html.ts` - Markdown to HTML
- `packages/core/src/providers/html/index.ts` - HTML processor
- `packages/core/__tests__/data/md/` - Test fixtures

From https://github.com/streetwriters/notesnook:
- `apps/web/src/utils/importer.ts` - Web importer
- Documentation in `docs/help/contents/importing-notes/`

## Recommendations for apple-notes-to-google-keep Project

1. **For Notesnook export**: Use the YAML frontmatter format with ISO 8601 dates
2. **For attachments**: Create `attachments/` subdirectory and use relative paths
3. **For tags**: Use comma-separated format (simpler than arrays)
4. **For content**: Ensure valid markdown that follows CommonMark spec
5. **For distribution**: Consider ZIP packaging with embedded attachment files
6. **For testing**: Import into Notesnook via Settings > Importer > Markdown
7. **For compatibility**: Don't rely on unsupported features like arbitrary colors or stored markdown

## Quick Test

To verify format compatibility:
1. Create a test markdown file with frontmatter
2. Add a test image in `attachments/` subdirectory
3. Import via Notesnook web app
4. Verify all metadata, images, and formatting imported correctly

