# Notesnook Markdown Import - Code Reference

Complete code references from the Notesnook importer codebase for understanding the exact implementation.

## 1. Markdown Provider (Core Processor)

**File**: `packages/core/src/providers/md/index.ts`

```typescript
export type MarkdownSettings = ProviderSettings & {
  filenameAsTitle?: boolean;
};

export class Markdown implements IFileProvider<MarkdownSettings> {
  id: Providers = "md";
  type = "file" as const;
  supportedExtensions = [".md", ".markdown", ".mdown"];
  version = "1.0.0";
  name = "Markdown";
  examples = ["document.md"];

  filter(file: File) {
    return this.supportedExtensions.includes(file.extension);
  }

  async *process(
    file: File,
    settings: MarkdownSettings,
    files: File[]
  ): AsyncGenerator<ProviderMessage, void, unknown> {
    // 1. Read file content
    const text = await file.text();
    
    // 2. Parse frontmatter
    const { content, frontmatter } = parseFrontmatter(text);
    
    // 3. Convert markdown to HTML
    const html = markdowntoHTML(content);
    
    // 4. Process HTML for attachments
    const note = await HTML.processHTML(file, files, settings.hasher, html);
    
    // 5. Apply frontmatter metadata
    note.title = settings.filenameAsTitle
      ? file.nameWithoutExtension
      : note.title;
      
    if (frontmatter) {
      note.title = frontmatter.title || note.title;
      
      // Handle tags (supports both string and array)
      note.tags = cleanupTags(
        Array.isArray(frontmatter.tags)
          ? frontmatter.tags
          : frontmatter.tags?.split(",") || []
      );
      
      note.pinned = frontmatter.pinned;
      note.favorite = frontmatter.favorite;
      
      // Handle created date with fallback field names
      const dateCreated = getPropertyWithFallbacks(
        frontmatter,
        ["created", "created_at", "date created"],
        note.dateCreated
      );
      if (dateCreated !== undefined) {
        note.dateCreated = new Date(dateCreated).getTime();
      }
      
      // Handle updated date with fallback field names
      const dateEdited = getPropertyWithFallbacks(
        frontmatter,
        ["updated", "updated_at", "date updated"],
        note.dateEdited
      );
      if (dateEdited !== undefined) {
        note.dateEdited = new Date(dateEdited).getTime();
      }
      
      note.color = frontmatter.color;
    }
    
    yield { type: "note", note };
  }
}

// Helper functions
function getPropertyWithFallbacks<T, R>(
  obj: T,
  properties: (keyof T)[],
  fallback: R
): R {
  for (const property of properties) {
    if (obj[property]) return obj[property] as R;
  }
  return fallback;
}

function cleanupTags(tags: string[]) {
  return tags.map((tag) => tag.replace("#", "").trim());
}
```

## 2. Frontmatter Parser

**File**: `packages/core/src/utils/frontmatter.ts`

```typescript
import matter from "gray-matter";

export interface Result {
  frontmatter?: {
    title?: string;
    tags?: string | string[];
    pinned?: boolean;
    favorite?: boolean;

    created_at?: string;
    updated_at?: string;
    edited_at?: string;
    created?: string;
    updated?: string;
    edited?: string;
    ["created-at"]?: string;
    ["updated-at"]?: string;
    ["edited-at"]?: string;
    ["date created"]?: string;
    ["date updated"]?: string;
    ["date edited"]?: string;

    color?: string;
  };
  content: string;
}

export function parseFrontmatter(input: string): Result {
  const { content, data } = matter(input);
  return {
    content,
    frontmatter: data
  };
}
```

Key points:
- Uses `gray-matter` library for YAML parsing
- Supports multiple field name variants for dates
- Frontmatter is optional

## 3. Markdown to HTML Converter

**File**: `packages/core/src/utils/to-html.ts`

Key processing pipeline:

```typescript
export function markdowntoHTML(
  src: string,
  options: { allowDangerousHtml: boolean; encodeHtmlEntities?: boolean } = {
    allowDangerousHtml: true,
    encodeHtmlEntities: true
  }
) {
  const result = remark()
    .use(remarkGfm, { singleTilde: false })           // GitHub Flavored
    .use(remarkMath)                                   // Math equations
    .use(remarkSubSuper)                              // Superscript/subscript
    .use(remarkHighlight)                             // Highlights
    .use(removeComments)                              // Obsidian comments
    .use(convertFileEmbeds)                           // Wiki-style embeds
    .use(remarkRehype, { allowDangerousHtml: options.allowDangerousHtml })
    .use(escapeCode)
    .use(fixChecklistClasses)                         // Task lists
    .use(liftLanguageToPreFromCode)
    .use(collapseMultilineParagraphs)
    .use(rehypeStringify, {
      allowDangerousHtml: options.allowDangerousHtml,
      tightSelfClosing: true,
      closeSelfClosing: true,
      closeEmptyElements: true,
      characterReferences: {
        useShortestReferences: true
      }
    })
    .processSync(src);
  return result.value as string;
}
```

Special syntax support examples from tests:

```markdown
# Highlights
==highlighted text==  → <span style="background-color: rgb(255, 255, 0);">highlighted text</span>

# Subscript/Superscript
H~2~O  → H<sub>2</sub>O
19^th^ → 19<sup>th</sup>

# Math
$2+2$         → <span class="math math-inline">2+2</span>
$$formula$$   → <div class="math math-display">formula</div>

# Task lists
- [ ] Task 1  → <li class="checklist--item">Task 1</li>
- [x] Task 2  → <li class="checklist--item checked">Task 2</li>

# Code blocks with language
```python
code
```
→ <pre class="language-python"><code class="language-python">code</code></pre>

# Obsidian comments (REMOVED in output)
Text %%comment%% more  → Text more

# Wiki embeds
![[image.jpg]]          → <a href="image.jpg"></a>
![[image.jpg|100x100]]  → <a href="image.jpg" width="100" height="100"></a>
```

## 4. HTML Processor (Attachment Handling)

**File**: `packages/core/src/providers/html/index.ts`

Key methods:

```typescript
export class HTML implements IFileProvider {
  id: Providers = "html";
  type = "file" as const;
  supportedExtensions = [".html", ".htm"];

  static async processHTML(
    file: File,
    files: File[],
    hasher: IHasher,
    html: string,
    processResource?: ResourceHandler
  ): Promise<Note> {
    const document = parseDocument(html);

    // Extract title from <title>, <h1>, or <h2>
    const titleElement = findOne(
      (e) => ["title", "h1", "h2"].includes(e.tagName),
      document.childNodes,
      true
    );
    const title = titleElement
      ? textContent(titleElement)
      : file.nameWithoutExtension;

    // Extract and process attachments from img/video/audio/links
    const resources = await HTML.extractResources(
      document,
      file,
      files,
      hasher,
      processResource
    );

    const note: Note = {
      title: title,
      dateCreated: file.createdAt,        // File timestamp
      dateEdited: file.modifiedAt,        // File timestamp
      attachments: [...resources],
      notebooks: rootNotebook ? [rootNotebook] : [],
      content: {
        type: ContentType.HTML,
        data: body ? render(body.childNodes) : render(document.childNodes)
      }
    };

    // Extract metadata from HTML meta tags
    HTML.setNoteMetadata(note, document);

    return note;
  }

  private static async extractResources(
    document: Document,
    file: File,
    files: File[],
    hasher: IHasher,
    processResource?: ResourceHandler
  ) {
    // Find all resource elements
    const resources = findAll(
      (elem) => RESOURCE_TAGS.includes(elem.tagName.toLowerCase()),
      document.childNodes
    );

    const attachments: Attachment[] = [];
    for (const resource of resources) {
      // Try to resolve file
      const resourceFile =
        (await processResource?.(resource)?.catch(() => undefined)) ||
        (await defaultResourceHandler(resource, file, files));
      
      if (!resourceFile) continue;

      const data = await resourceFile.bytes();
      if (!data) continue;

      // Hash the file
      const dataHash = await hasher.hash(data);
      const mimeType = detectFileType(data);
      const filename =
        resource.attribs.title ||
        resource.attribs.filename ||
        resourceFile.name ||
        dataHash;

      const attachment: Attachment = {
        data,
        size: data.byteLength,
        hash: dataHash,
        filename: appendExtension(filename, mimeType?.ext),
        hashType: hasher.type,
        mime:
          mimeType?.mime ||
          resource.attribs.mime ||
          `application/octet-stream`
      };
      attachments.push(attachment);

      // Replace resource in HTML with attachment reference
      replaceElement(resource, parseDocument(attachmentToHTML(attachment)));
    }
    return attachments;
  }

  private static setNoteMetadata(note: Note, document: Document) {
    // Extract metadata from <meta> tags
    const metaTags = getElementsByTagName("meta", document, true);
    for (const tag of metaTags) {
      const name = getAttributeValue(tag, "name");
      const content = getAttributeValue(tag, "content");
      if (!name || !content) continue;

      switch (name) {
        case "created-on":
        case "created-at":
        case "created":
          note.dateCreated = new Date(content).getTime();
          break;
        case "last-edited-on":
        case "edited-at":
        case "edited":
        case "updated-at":
        case "updated":
          note.dateEdited = new Date(content).getTime();
          break;
        case "pinned":
          note.pinned = content === "true";
          break;
        case "favorite":
          note.favorite = content === "true";
          break;
        case "color":
          note.color = content;
          break;
      }
    }
  }
}

// File resolution for attachments
async function defaultResourceHandler(
  resource: Element,
  file: File,
  files: File[]
) {
  const src =
    getAttributeValue(resource, "src") || getAttributeValue(resource, "href");
  const fullPath =
    src &&
    file?.path &&
    decodeURIComponent(path.join(path.dirname(file.path), src));
  if (!fullPath) return;

  return files.find((file) => file.path === fullPath);
}
```

## 5. Web Importer Integration

**File**: `apps/web/src/utils/importer.ts`

How notes are imported into Notesnook database:

```typescript
export async function importNote(note: Note) {
  // Process attachments with encryption
  const encryptedAttachmentFieldsMap = await processAttachments(
    note.attachments
  );
  await processNote(note, encryptedAttachmentFieldsMap);
}

async function processNote(
  note: Note,
  map: Record<string, EncryptedAttachmentFields | undefined>
) {
  // Add attachments to database
  for (const attachment of note.attachments || []) {
    const cipherData = map[attachment.hash];
    if (!cipherData || (await db.attachments?.exists(attachment.hash))) {
      continue;
    }

    await db.attachments?.add({
      ...cipherData,
      hash: attachment.hash,
      hashType: attachment.hashType,
      filename: attachment.filename,
      mimeType: attachment.mime
    });
  }

  // Ensure content has HTML type
  if (!note.content)
    note.content = {
      data: "<p></p>",
      type: ContentType.HTML
    };

  if (note.content?.type === "html") (note.content.type as string) = "tiptap";

  // Add note to database
  const noteId = await db.notes.add({
    ...note,
    content: { type: "tiptap", data: note.content?.data },
    notebooks: []
  });

  // Add tags
  for (const tag of note.tags || []) {
    const tagId =
      (await db.tags.find(tag))?.id ||
      (await db.tags.add({
        title: tag
      }));
    if (!tagId) continue;

    await db.relations.add(
      {
        id: tagId,
        type: "tag"
      },
      {
        id: noteId,
        type: "note"
      }
    );
  }

  // Add color
  const colorCode = note.color ? colorMap[note.color] : undefined;
  if (colorCode) {
    const colorId =
      (await db.colors.find(colorCode))?.id ||
      (await db.colors.add({
        colorCode: colorCode,
        title: note.color
      }));

    await db.relations.add(
      {
        id: colorId,
        type: "color"
      },
      {
        id: noteId,
        type: "note"
      }
    );
  }
}

const colorMap: Record<string, string | undefined> = {
  default: undefined,
  teal: "#00897B",
  red: "#D32F2F",
  purple: "#7B1FA2",
  blue: "#1976D2",
  cerulean: "#03A9F4",
  pink: "#C2185B",
  brown: "#795548",
  gray: "#9E9E9E",
  green: "#388E3C",
  orange: "#FFA000",
  yellow: "#FFC107"
};
```

## Key Takeaways for Implementation

1. **Frontmatter parsing is flexible** - supports multiple field name variants
2. **Markdown is converted to HTML** - not stored as markdown internally
3. **Attachments are resolved via relative paths** - must exist in file set
4. **Tags support both formats** - comma-separated string or array
5. **Dates are converted to millisecond timestamps** - use ISO 8601 in frontmatter
6. **Colors map to specific values** - only 11 colors supported
7. **Wiki-style syntax is supported** - `![[file]]` format is converted to HTML links
8. **Comments are stripped** - `%%...%%` is removed during processing
9. **File structure doesn't create notebooks** - directory hierarchy is optional
10. **No strict ordering required** - process order doesn't affect result

## Testing Files

Located in `packages/core/__tests__/data/md/`:
- `md-with-frontmatter.md` - Complete example with all frontmatter fields
- `test.md` - Example without frontmatter
- `test2.md` - Additional test case with mixed content

