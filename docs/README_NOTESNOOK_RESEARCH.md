# Notesnook Export Research Documentation

Complete research on Notesnook markdown import format with implementation guides and code references.

## Documents Included

### 1. NOTESNOOK_RESEARCH_SUMMARY.md
**START HERE** - Executive summary with TL;DR and quick reference.
- What Notesnook expects
- Key format details
- Processing pipeline
- Implementation notes
- Validation checklist
- Recommendations for the project

### 2. NOTESNOOK_IMPORT_FORMAT.md
Comprehensive specification of the Notesnook markdown import format.
- Supported markdown formats (CommonMark, GFM, Obsidian, Math, etc.)
- YAML frontmatter field reference
- Supported colors and their mappings
- Tag field handling
- Date parsing details
- Attachment/image handling
- Complete example markdown file
- Output format specification
- Test data locations

### 3. NOTESNOOK_IMPLEMENTATION_GUIDE.md
TypeScript implementation templates and helpers.
- Export function template
- Frontmatter generation
- Tag formatting
- YAML escaping
- Color mapping functions
- Date conversion
- Attachment handling
- Validation checklist
- Testing recommendations

### 4. NOTESNOOK_CODE_REFERENCE.md
Complete source code excerpts from Notesnook importer.
- Markdown provider class (`md/index.ts`)
- Frontmatter parser (`frontmatter.ts`)
- Markdown to HTML converter (`to-html.ts`)
- HTML processor for attachments (`html/index.ts`)
- Web importer integration
- Key takeaways
- Test file locations

## Quick Start

For a quick implementation:

1. Read **NOTESNOOK_RESEARCH_SUMMARY.md** (5 min)
2. Review **NOTESNOOK_IMPLEMENTATION_GUIDE.md** (10 min)
3. Implement using TypeScript templates
4. Reference **NOTESNOOK_CODE_REFERENCE.md** as needed

## Key Findings

### Markdown Format
- YAML frontmatter at the beginning
- Supports CommonMark + GFM + Obsidian syntax
- Markdown converted to HTML internally

### Metadata Fields
```yaml
title: string
tags: comma-separated or array
pinned: boolean
favorite: boolean
created_at: ISO 8601 date
updated_at: ISO 8601 date
color: blue|red|green|orange|yellow|purple|pink|teal|cerulean|brown|gray
```

### Attachments
- Referenced via relative paths: `![alt](attachments/image.jpg)`
- ZIP recommended for distribution
- MIME types auto-detected

### Critical Details
- Frontmatter optional (title from first H1 or filename)
- Dates support multiple field names (created, created_at, created-at, date created)
- Tags support both formats: comma-separated or YAML array
- Only 11 colors supported
- Obsidian comments `%%...%%` are removed
- No automatic notebook creation from directories

## Implementation Checklist

- [ ] Create markdown files with `.md` extension
- [ ] Add YAML frontmatter with metadata
- [ ] Use ISO 8601 for dates (e.g., 2023-06-06T09:00:00.000Z)
- [ ] Create `attachments/` subdirectory for files
- [ ] Use relative paths in markdown: `![alt](attachments/image.jpg)`
- [ ] Use comma-separated tags format
- [ ] Validate color values
- [ ] Escape special characters in YAML
- [ ] Test import in Notesnook app
- [ ] Optionally ZIP files for distribution

## Sources

Research based on:
- https://github.com/streetwriters/notesnook
- https://github.com/streetwriters/notesnook-importer
- Live Notesnook web application at https://app.notesnook.com

Research completed: 2025-11-08

## Files Referenced

### From notesnook-importer
- `packages/core/src/providers/md/index.ts` - Markdown provider
- `packages/core/src/utils/frontmatter.ts` - YAML parsing
- `packages/core/src/utils/to-html.ts` - Markdown conversion
- `packages/core/src/providers/html/index.ts` - HTML processing
- `packages/core/__tests__/data/md/` - Test examples

### From notesnook
- `apps/web/src/utils/importer.ts` - Web importer
- `docs/help/contents/importing-notes/` - Documentation

## Notes for apple-notes-to-google-keep Project

This research supports adding Notesnook as an export format to the apple-notes-to-google-keep project. The documented format, implementation guides, and code references provide everything needed to:

1. Convert Apple Notes to Notesnook-compatible markdown
2. Handle metadata (dates, tags, colors, pinned, favorite)
3. Process attachments (images, files)
4. Package for import via Notesnook's importer
5. Maintain content fidelity during export

All information is current as of November 8, 2025, based on the latest Notesnook importer code.

