"""Export notes to Notesnook markdown format."""

from pathlib import Path
from typing import List
from datetime import datetime
from .apple_notes import AppleNote


class NotesnookExporter:
    """Exports Apple Notes to Notesnook markdown format with YAML frontmatter."""

    def export_notes(self, notes: List[AppleNote], output_dir: Path, attachments_dir: str = "attachments") -> int:
        """Export notes to Notesnook markdown format.

        Notesnook expects markdown files with YAML frontmatter:
        ---
        title: Note Title
        created: 2024-01-15T10:30:00.000Z
        updated: 2024-01-20T15:45:00.000Z
        ---

        Note content here.

        Args:
            notes: List of Apple Notes to export.
            output_dir: Directory to write exported markdown files.
            attachments_dir: Name of attachments directory (relative path for markdown refs).

        Returns:
            Number of notes successfully exported.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        successful = 0

        for i, note in enumerate(notes):
            try:
                # Create safe filename from title
                safe_title = self._sanitize_filename(note.title or f"Untitled_{i}")
                filename = f"{safe_title}_{i}.md"
                file_path = output_dir / filename

                # Write markdown file with YAML frontmatter
                self._write_markdown(note, file_path, attachments_dir)

                successful += 1
                print(f"✓ Exported: {note.title}")

            except Exception as e:
                print(f"✗ Failed to export '{note.title}': {e}")

        return successful

    def _write_markdown(self, note: AppleNote, path: Path, attachments_dir: str) -> None:
        """Write note as markdown file with YAML frontmatter.

        Args:
            note: The Apple Note to export.
            path: Path to write markdown file.
            attachments_dir: Name of attachments directory for image references.
        """
        # Build YAML frontmatter
        frontmatter = ["---"]
        frontmatter.append(f"title: {self._escape_yaml_string(note.title or 'Untitled')}")

        # Add created date in ISO 8601 format
        if note.created_date:
            created_iso = self._format_datetime_iso(note.created_date)
            frontmatter.append(f"created: {created_iso}")

        # Add updated date in ISO 8601 format
        if note.modified_date:
            updated_iso = self._format_datetime_iso(note.modified_date)
            frontmatter.append(f"updated: {updated_iso}")

        # Add folder as tag if present
        if note.folder:
            frontmatter.append(f"tags: {self._escape_yaml_string(note.folder)}")

        frontmatter.append("---")

        # Build content
        content = note.content or ""

        # Process content to handle any attachment references
        # Apple Notes might have references that need to be converted
        content = self._process_content_for_attachments(content, attachments_dir)

        # Clean up problematic characters
        content = self._clean_content(content)

        # Combine frontmatter and content
        markdown = "\n".join(frontmatter) + "\n\n" + content

        path.write_text(markdown, encoding='utf-8')

    def _format_datetime_iso(self, dt: datetime) -> str:
        """Format datetime as ISO 8601 string.

        Args:
            dt: datetime object.

        Returns:
            ISO 8601 formatted string (e.g., '2024-01-15T10:30:00.000Z').
        """
        # Convert to UTC and format as ISO 8601
        # Apple Notes dates are in local time, so we'll use them as-is
        # Format: YYYY-MM-DDTHH:MM:SS.sssZ
        return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    def _escape_yaml_string(self, s: str) -> str:
        """Escape string for YAML frontmatter.

        Args:
            s: String to escape.

        Returns:
            Escaped string, quoted if necessary.
        """
        # If string contains special characters, wrap in quotes
        special_chars = [':', '#', '-', '[', ']', '{', '}', ',', '&', '*', '!', '|', '>', "'", '"', '%', '@', '`']

        if any(char in s for char in special_chars) or s.startswith(' ') or s.endswith(' '):
            # Use double quotes and escape any internal quotes
            escaped = s.replace('\\', '\\\\').replace('"', '\\"')
            return f'"{escaped}"'

        return s

    def _process_content_for_attachments(self, content: str, attachments_dir: str) -> str:
        """Process content to convert attachment references to Notesnook format.

        Args:
            content: Note content.
            attachments_dir: Name of attachments directory.

        Returns:
            Processed content with proper markdown image syntax.
        """
        # This is a placeholder for more sophisticated attachment processing
        # If Apple Notes content contains attachment references, convert them
        # to markdown image syntax: ![description](attachments/filename.ext)

        # For now, just return content as-is
        # You may need to enhance this based on what attachment references
        # look like in your Apple Notes export

        return content

    def _clean_content(self, content: str) -> str:
        """Clean content of problematic characters.

        Args:
            content: Note content.

        Returns:
            Cleaned content.
        """
        # Remove Apple Notes object replacement characters and other control characters
        # The '\ufffc' character is used as an object replacement character in Apple Notes
        content = content.replace('\ufffc', '[attachment]')  # Mark where attachments were

        # Remove other common problematic characters from Apple Notes
        # Replace fancy quotes with regular quotes
        content = content.replace('\u2018', "'").replace('\u2019', "'")  # Single quotes
        content = content.replace('\u201c', '"').replace('\u201d', '"')  # Double quotes

        # Replace em/en dashes with regular dashes
        content = content.replace('\u2013', '-').replace('\u2014', '-')

        # Replace non-breaking spaces with regular spaces
        content = content.replace('\xa0', ' ')

        # Remove common encoding artifacts
        content = content.replace('â', '-')  # Often appears as em-dash artifact
        content = content.replace('Â', '')   # Non-breaking space artifact
        content = content.replace('Ã', '')   # Various encoding artifacts
        content = content.replace('ï¿¼', '')  # Object replacement artifact

        # Strip trailing whitespace and ensure single newline at end
        content = content.strip()

        # Clean up multiple consecutive blank lines
        import re
        content = re.sub(r'\n\n\n+', '\n\n', content)

        # Remove trailing non-alphanumeric characters that are likely artifacts
        # from Apple Notes truncation (but preserve intentional punctuation)
        while content and content[-1] in '\ufffc\u00e2\u00a0\x00âÂïï¿¼':
            content = content[:-1].rstrip()

        return content

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to be filesystem-safe.

        Args:
            filename: Original filename.

        Returns:
            Sanitized filename.
        """
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Limit length
        if len(filename) > 100:
            filename = filename[:100]

        # Remove leading/trailing spaces and dots
        filename = filename.strip('. ')

        return filename or "Untitled"
