# Notesnook Export Implementation Guide

Based on the research of the Notesnook importer codebase, this guide provides implementation details for exporting to Notesnook format.

## Quick Summary

Notesnook expects:
1. Markdown files (`.md`, `.markdown`, `.mdown`)
2. YAML frontmatter for metadata
3. HTML content (automatically generated from markdown)
4. Attachments resolved via relative file paths
5. Optional ZIP archive containing files and attachments

## Export Function Template

```typescript
interface NotesnookFrontmatter {
  title?: string;
  tags?: string | string[];
  pinned?: boolean;
  favorite?: boolean;
  created?: string;           // ISO 8601
  created_at?: string;        // ISO 8601
  updated?: string;           // ISO 8601
  updated_at?: string;        // ISO 8601
  color?: 'blue' | 'red' | 'green' | 'orange' | 'yellow' | 
          'purple' | 'pink' | 'teal' | 'cerulean' | 'brown' | 'gray';
}

interface NotesnookNote {
  filename: string;           // e.g., "note-title.md"
  frontmatter: NotesnookFrontmatter;
  content: string;            // Markdown content (WITHOUT frontmatter)
  attachments?: {
    filename: string;
    path: string;             // Relative path for resolution
    mimeType: string;
  }[];
}

async function exportToNotesnook(
  notes: NoteData[],
  outputDir: string
): Promise<void> {
  for (const note of notes) {
    const notesnookNote: NotesnookNote = {
      filename: sanitizeFilename(note.title || 'untitled'),
      frontmatter: {
        title: note.title,
        created_at: new Date(note.createdAt).toISOString(),
        updated_at: new Date(note.updatedAt).toISOString(),
        tags: note.tags || [],
        pinned: note.pinned || false,
        favorite: note.favorite || false,
        color: mapColorToNotesnook(note.color)
      },
      content: note.content,
      attachments: note.attachments?.map(att => ({
        filename: att.filename,
        path: `attachments/${att.filename}`,
        mimeType: att.mimeType
      }))
    };

    // Write markdown file with frontmatter
    const mdContent = generateMarkdownWithFrontmatter(notesnookNote);
    await fs.writeFile(
      path.join(outputDir, notesnookNote.filename + '.md'),
      mdContent
    );

    // Copy attachments
    if (notesnookNote.attachments) {
      const attachDir = path.join(outputDir, 'attachments');
      await fs.mkdir(attachDir, { recursive: true });
      for (const att of notesnookNote.attachments) {
        await copyFile(att.originalPath, path.join(attachDir, att.filename));
      }
    }
  }
}

function generateMarkdownWithFrontmatter(note: NotesnookNote): string {
  const fm = note.frontmatter;
  const frontmatter = [
    '---',
    `title: ${escapeYaml(fm.title || 'Untitled')}`,
    fm.tags && fm.tags.length ? `tags: ${formatTags(fm.tags)}` : null,
    fm.pinned ? 'pinned: true' : null,
    fm.favorite ? 'favorite: true' : null,
    fm.created_at ? `created_at: ${fm.created_at}` : null,
    fm.updated_at ? `updated_at: ${fm.updated_at}` : null,
    fm.color ? `color: ${fm.color}` : null,
    '---',
    ''
  ]
    .filter(Boolean)
    .join('\n');

  return frontmatter + note.content;
}

function formatTags(tags: string | string[]): string {
  if (Array.isArray(tags)) {
    return tags.map(t => t.trim()).join(', ');
  }
  return tags.split(',').map(t => t.trim()).join(', ');
}

function escapeYaml(str: string): string {
  // YAML strings with special characters should be quoted
  if (str.includes(':') || str.includes('[') || str.includes(']') || 
      str.includes(',') || str.includes('#') || str.includes('&') ||
      str.includes('*') || str.includes('!') || str.includes('|') ||
      str.includes('>')) {
    return `"${str.replace(/"/g, '\\"')}"`;
  }
  return str;
}
```

## Attachment Handling

Key requirements:
1. **Path resolution**: Relative paths from markdown file to attachments
2. **File hashing**: Not required (Notesnook generates hashes on import)
3. **MIME types**: Auto-detected on import, but can be specified
4. **Recommended structure**:
   ```
   output/
     note1.md
     note2.md
     attachments/
       image1.jpg
       image2.png
       document.pdf
   ```

5. **ZIP packaging** (recommended):
   ```bash
   zip -r notes_export.zip output/
   # Then import notes_export.zip into Notesnook
   ```

## Markdown Content Requirements

When generating markdown content:
- Use standard markdown syntax for basic formatting
- For advanced features, use:
  - `==text==` for highlighting (yellow background)
  - `19^th^` for superscript, `H~2~O` for subscript
  - ` ```lang\ncode\n``` ` for code blocks with syntax highlighting
  - `- [ ]` and `- [x]` for task lists
  - `| col | col |` for tables (GFM)
  - `![alt](path)` for images
  - `![[file.pdf|100x100]]` for wiki-style embeds (Obsidian)

- Image/attachment references must use:
  - Standard markdown: `![alt](attachments/image.jpg)`
  - OR wiki-style: `![[image.jpg]]` (if in same directory)

## Color Mapping

Map colors to supported Notesnook values:

```typescript
const colorMap: Record<string, string> = {
  'red': 'red',
  'orange': 'orange',
  'yellow': 'yellow',
  'green': 'green',
  'teal': 'teal',
  'blue': 'blue',
  'purple': 'purple',
  'pink': 'pink',
  'brown': 'brown',
  'gray': 'gray',
  'grey': 'gray',
  'default': undefined
};

function mapColorToNotesnook(appleColor: string | null): string | undefined {
  if (!appleColor) return undefined;
  return colorMap[appleColor.toLowerCase()];
}
```

## Date Handling

Important: Notesnook stores dates as Unix timestamps (milliseconds):

```typescript
function toNotesnookDate(date: Date | string | number): string {
  // Always return ISO 8601 string for frontmatter
  // Notesnook's importer will convert to timestamp
  if (typeof date === 'number') {
    return new Date(date).toISOString();
  }
  return new Date(date).toISOString();
}
```

## Tag Handling

Best practice for tags:

```typescript
function formatNotesnookTags(tags: string[]): string {
  return tags
    .map(tag => tag.trim())
    .filter(tag => tag.length > 0)
    .map(tag => tag.startsWith('#') ? tag.slice(1) : tag)
    .join(', ');  // or use array format: tags: [tag1, tag2]
}
```

## Validation Checklist

Before export:
- [ ] All markdown files have `.md` extension
- [ ] YAML frontmatter is at the beginning of each file
- [ ] All dates in frontmatter are ISO 8601 format
- [ ] All image references have correct relative paths
- [ ] Attachment files exist at referenced paths
- [ ] Tag names don't have special characters
- [ ] Color names are from supported list
- [ ] No frontmatter YAML has unescaped special characters
- [ ] Files are properly encoded (UTF-8)

## Testing

Create test files matching the examples found in Notesnook test data:

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

# Content heading

Your markdown content here with various **formatting** options.

![Image](attachments/example.jpg)
```

Then import into Notesnook via Settings > Notesnook Importer > Markdown

## References

- Notesnook importer: https://github.com/streetwriters/notesnook-importer
- Markdown provider: `packages/core/src/providers/md/index.ts`
- Frontmatter parser: `packages/core/src/utils/frontmatter.ts`
- Markdown to HTML: `packages/core/src/utils/to-html.ts`
- HTML processor: `packages/core/src/providers/html/index.ts`
