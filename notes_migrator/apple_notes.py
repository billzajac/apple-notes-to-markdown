"""Extract notes from Apple Notes database."""

import sqlite3
import os
import gzip
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from protobuf_inspector.types import StandardParser


@dataclass
class AppleNote:
    """Represents a note extracted from Apple Notes."""

    title: str
    content: str
    created_date: Optional[datetime]
    modified_date: Optional[datetime]
    folder: Optional[str]
    pinned: bool = False
    attachments: List[Dict[str, Any]] = field(default_factory=list)


class AppleNotesExtractor:
    """Extracts notes from the Apple Notes SQLite database."""

    DEFAULT_DB_PATH = Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
    DEFAULT_MEDIA_BASE = Path.home() / "Library/Group Containers/group.com.apple.notes/Accounts"

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize extractor with database path.

        Args:
            db_path: Path to Notes database. Uses default location if None.
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.media_base = self.DEFAULT_MEDIA_BASE

        if not self.db_path.exists():
            raise FileNotFoundError(
                f"Apple Notes database not found at {self.db_path}. "
                "Make sure you're running this on macOS with Apple Notes installed."
            )

    def extract_all_notes(self) -> List[AppleNote]:
        """Extract all notes from the database.

        Returns:
            List of AppleNote objects.
        """
        notes = []

        try:
            self.conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = self.conn.cursor()

            # Query to get notes with their content and metadata
            # Apple Notes stores content in ZICCLOUDSYNCINGOBJECT table
            query = """
                SELECT
                    n.Z_PK,
                    n.ZTITLE1 as title,
                    n.ZSNIPPET as snippet,
                    n.ZCREATIONDATE1 as created,
                    n.ZMODIFICATIONDATE1 as modified,
                    f.ZTITLE2 as folder,
                    c.ZDATA as content_data,
                    n.ZISPINNED as is_pinned
                FROM ZICCLOUDSYNCINGOBJECT n
                LEFT JOIN ZICCLOUDSYNCINGOBJECT f ON n.ZFOLDER = f.Z_PK
                LEFT JOIN ZICNOTEDATA c ON n.ZNOTEDATA = c.Z_PK
                WHERE n.ZTITLE1 IS NOT NULL
                    AND n.ZMARKEDFORDELETION = 0
                ORDER BY n.ZMODIFICATIONDATE1 DESC
            """

            cursor.execute(query)
            rows = cursor.fetchall()

            for row in rows:
                pk, title, snippet, created, modified, folder, content_data, is_pinned = row

                # Extract text content and attachments together
                content, attachments = self._extract_content_and_attachments(pk, content_data, snippet)

                # Remove title from beginning of content if present
                # Apple Notes includes the title as the first line
                # We need to adjust attachment positions after removing the title
                title_offset = 0
                if content and title:
                    # Check if content starts with the title (possibly followed by newline)
                    if content.startswith(title):
                        # Calculate how many characters we're removing
                        title_with_newlines = title
                        remaining = content[len(title):]
                        # Count newlines being stripped
                        stripped = remaining.lstrip('\n')
                        title_offset = len(title) + (len(remaining) - len(stripped))

                        # Remove title and any following newlines
                        content = stripped

                        # Adjust attachment positions by subtracting the title offset
                        for attachment in attachments:
                            if 'position' in attachment:
                                attachment['position'] -= title_offset

                # Convert Apple's time format (seconds since 2001-01-01)
                created_date = self._convert_apple_timestamp(created)
                modified_date = self._convert_apple_timestamp(modified)

                note = AppleNote(
                    title=title or "Untitled",
                    content=content,
                    created_date=created_date,
                    modified_date=modified_date,
                    folder=folder,
                    pinned=bool(is_pinned) if is_pinned else False,
                    attachments=attachments
                )
                notes.append(note)

            self.conn.close()

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to read Apple Notes database: {e}")

        return notes

    def _extract_content_and_attachments(self, note_pk: int, content_data: Optional[bytes], snippet: Optional[str]) -> tuple[str, List[Dict[str, Any]]]:
        """Extract readable text and file attachments from note content data.

        Args:
            note_pk: Primary key of the note.
            content_data: Binary content data from database.
            snippet: Text snippet as fallback.

        Returns:
            Tuple of (text_content, attachments_list).
        """
        if not content_data:
            return snippet or "", []

        try:
            # Check if it's gzipped (magic bytes 0x1f 0x8b)
            is_gzipped = len(content_data) >= 2 and content_data[0] == 0x1f and content_data[1] == 0x8b

            if is_gzipped:
                # Decompress the gzipped protobuf data
                decompressed = gzip.decompress(content_data)
            else:
                # Legacy iOS 8 format - plain text
                decompressed = content_data

            # Try to parse as protobuf
            text, attachments = self._parse_protobuf_with_attachments(note_pk, decompressed)

            # If parsing fails or result is too short, fall back to snippet
            if not text or len(text.strip()) < 3:
                return snippet or "", []

            return text.strip(), attachments

        except Exception as e:
            # If decompression or parsing fails, fall back to snippet
            return snippet or "", []

    def _extract_content(self, content_data: Optional[bytes], snippet: Optional[str]) -> str:
        """Extract readable text from note content data.

        Args:
            content_data: Binary content data from database.
            snippet: Text snippet as fallback.

        Returns:
            Extracted text content.
        """
        # This is now a wrapper for backward compatibility
        content, _ = self._extract_content_and_attachments(0, content_data, snippet)
        return content

    def _parse_protobuf_with_attachments(self, note_pk: int, data: bytes) -> tuple[str, List[Dict[str, Any]]]:
        """Parse protobuf data to extract clean note text and file attachments.

        Apple Notes uses a protobuf structure:
        NoteStoreProto > Document > Note > note_text

        Args:
            note_pk: Primary key of the note.
            data: Decompressed protobuf binary data.

        Returns:
            Tuple of (extracted_text, attachments_list).
        """
        try:
            # Import the generated protobuf classes
            from . import notestore_pb2

            # Parse using the proper schema
            note_store = notestore_pb2.NoteStoreProto()
            note_store.ParseFromString(data)

            # Navigate to the note text field
            # Structure: NoteStoreProto.document.note.note_text
            if note_store.HasField('document'):
                document = note_store.document
                if document.HasField('note'):
                    note = document.note
                    # This is the complete, clean note text
                    note_text = note.note_text

                    # Replace inline attachment markers and get positions for file attachments
                    # Returns (resolved_text, attachment_id_to_position_map)
                    note_text, attachment_positions = self._resolve_attachments(note_text, note.attribute_run)

                    # Extract file attachments using the position map
                    attachments = self._extract_attachments_with_positions(note_pk, note.attribute_run, attachment_positions)

                    return note_text.strip(), attachments

            # If we couldn't find the text field, fall back
            return self._extract_text_strings(data), []

        except Exception as e:
            # If protobuf parsing fails, fall back to string extraction
            return self._extract_text_strings(data), []

    def _parse_protobuf_content(self, data: bytes) -> str:
        """Parse protobuf data to extract clean note text.

        Apple Notes uses a protobuf structure:
        NoteStoreProto > Document > Note > note_text

        Args:
            data: Decompressed protobuf binary data.

        Returns:
            Extracted clean text.
        """
        # This is now a wrapper for backward compatibility
        text, _ = self._parse_protobuf_with_attachments(0, data)
        return text

    def _resolve_attachments(self, text: str, attribute_runs) -> tuple[str, dict]:
        """Replace \ufffc markers with actual attachment content.

        Args:
            text: Note text with \ufffc markers.
            attribute_runs: List of AttributeRun messages from protobuf.

        Returns:
            Tuple of (resolved_text, attachment_positions) where attachment_positions
            maps attachment_id to position in resolved text for file attachments.
        """
        try:
            # Build a list of (position, replacement, attachment_id, type_uti) tuples
            replacements = []
            pos = 0

            for attr_run in attribute_runs:
                # Check if this run has an attachment
                if attr_run.HasField('attachment_info'):
                    attachment_id = attr_run.attachment_info.attachment_identifier
                    type_uti = attr_run.attachment_info.type_uti

                    # Get the text segment for this run
                    text_segment = text[pos:pos + attr_run.length]

                    # Only process if it contains the attachment marker
                    if '\ufffc' in text_segment:
                        # Query database for attachment content
                        attachment_text = self._get_attachment_text(attachment_id, type_uti)
                        if attachment_text:
                            # Record this replacement (for inline attachments like hashtags)
                            marker_pos = pos + text_segment.index('\ufffc')
                            replacements.append((marker_pos, attachment_text, attachment_id, type_uti))
                        else:
                            # For file attachments, record position but don't replace yet
                            marker_pos = pos + text_segment.index('\ufffc')
                            replacements.append((marker_pos, None, attachment_id, type_uti))

                pos += attr_run.length

            # Apply replacements and track position changes
            attachment_positions = {}
            result = list(text)
            offset = 0  # Track cumulative position shift

            for marker_pos, replacement, attachment_id, type_uti in sorted(replacements, key=lambda x: x[0]):
                adjusted_pos = marker_pos + offset

                if replacement is not None:
                    # Inline attachment (hashtag, mention) - replace the marker
                    result[adjusted_pos] = replacement
                    # Update offset (replacement length - 1 for the marker we're replacing)
                    offset += len(replacement) - 1
                else:
                    # File attachment - record position in resolved text
                    attachment_positions[attachment_id] = adjusted_pos

            return ''.join(result), attachment_positions

        except Exception:
            # If attachment resolution fails, return original text with empty positions
            return text, {}

    def _get_attachment_text(self, attachment_id: str, type_uti: str) -> Optional[str]:
        """Get text content for an inline attachment.

        Args:
            attachment_id: UUID of the attachment.
            type_uti: Type UTI of the attachment.

        Returns:
            Text representation of the attachment, or None.
            Returns None for file attachments (images, PDFs, etc.) to preserve \ufffc markers.
        """
        try:
            if not hasattr(self, 'conn') or self.conn is None:
                return None

            cursor = self.conn.cursor()

            # Query for inline attachment content
            cursor.execute("""
                SELECT ZALTTEXT, ZTOKENCONTENTIDENTIFIER
                FROM ZICCLOUDSYNCINGOBJECT
                WHERE ZIDENTIFIER = ?
            """, (attachment_id,))

            row = cursor.fetchone()
            if row:
                alt_text, token = row
                # For hashtags and mentions, return the alt text
                if 'hashtag' in type_uti or 'mention' in type_uti:
                    return alt_text or ''
                # For file attachments (images, PDFs, etc.), return None
                # to preserve the \ufffc marker for later processing
                # The exporter will replace these with markdown image/link syntax
                return None

            return None

        except Exception:
            return None

    def _extract_attachments_with_positions(self, note_pk: int, attribute_runs, attachment_positions: dict) -> List[Dict[str, Any]]:
        """Extract file attachments using pre-calculated positions from resolved text.

        Args:
            note_pk: Primary key of the note in ZICCLOUDSYNCINGOBJECT.
            attribute_runs: List of AttributeRun from protobuf.
            attachment_positions: Map of attachment_id to position in resolved text.

        Returns:
            List of attachment dictionaries with file data.
        """
        attachments = []

        try:
            for attr_run in attribute_runs:
                if attr_run.HasField('attachment_info'):
                    attachment_id = attr_run.attachment_info.attachment_identifier
                    type_uti = attr_run.attachment_info.type_uti

                    # Skip inline attachments (hashtags, mentions) - already handled
                    if 'hashtag' in type_uti or 'mention' in type_uti:
                        continue

                    # Only process if we have a position for this attachment
                    if attachment_id not in attachment_positions:
                        continue

                    # Get attachment metadata from database
                    cursor = self.conn.cursor()

                    # Query for file attachment metadata and media UUID
                    # The ZMEDIA field points to another record in the same table
                    # that contains the actual media file UUID
                    cursor.execute("""
                        SELECT
                            att.ZIDENTIFIER as att_uuid,
                            att.ZTYPEUTI as att_uti,
                            att.ZFILENAME,
                            att.ZFILESIZE,
                            media.ZIDENTIFIER as media_uuid
                        FROM ZICCLOUDSYNCINGOBJECT att
                        LEFT JOIN ZICCLOUDSYNCINGOBJECT media ON att.ZMEDIA = media.Z_PK
                        WHERE att.ZIDENTIFIER = ?
                    """, (attachment_id,))

                    row = cursor.fetchone()
                    if row:
                        att_uuid, uti, filename, filesize, media_uuid = row

                        # Read media file from filesystem using the media UUID
                        media_result = self._read_media_file(media_uuid) if media_uuid else None

                        if media_result:
                            media_data, discovered_filename = media_result

                            # Determine filename (prefer database filename, then discovered, then generated)
                            final_filename = filename or discovered_filename
                            if not final_filename:
                                # Generate filename from UTI if no filename available
                                ext = self._get_extension_from_uti(uti or type_uti)
                                final_filename = f"{att_uuid[:8]}{ext}"

                            attachments.append({
                                'uuid': att_uuid,
                                'type_uti': uti or type_uti,
                                'filename': final_filename,
                                'data': media_data,
                                'position': attachment_positions[attachment_id]  # Use position from resolved text!
                            })

        except Exception as e:
            # If attachment extraction fails, continue without attachments
            pass

        return attachments

    def _extract_attachments(self, note_pk: int, attribute_runs) -> List[Dict[str, Any]]:
        """Extract file attachments for a note.

        Args:
            note_pk: Primary key of the note in ZICCLOUDSYNCINGOBJECT.
            attribute_runs: List of AttributeRun from protobuf.

        Returns:
            List of attachment dictionaries with file data.
        """
        attachments = []
        pos = 0

        try:
            for attr_run in attribute_runs:
                if attr_run.HasField('attachment_info'):
                    attachment_id = attr_run.attachment_info.attachment_identifier
                    type_uti = attr_run.attachment_info.type_uti

                    # Skip inline attachments (hashtags, mentions) - already handled
                    if 'hashtag' in type_uti or 'mention' in type_uti:
                        pos += attr_run.length
                        continue

                    # Get attachment metadata from database
                    cursor = self.conn.cursor()

                    # Query for file attachment metadata and media UUID
                    # The ZMEDIA field points to another record in the same table
                    # that contains the actual media file UUID
                    cursor.execute("""
                        SELECT
                            att.ZIDENTIFIER as att_uuid,
                            att.ZTYPEUTI as att_uti,
                            att.ZFILENAME,
                            att.ZFILESIZE,
                            media.ZIDENTIFIER as media_uuid
                        FROM ZICCLOUDSYNCINGOBJECT att
                        LEFT JOIN ZICCLOUDSYNCINGOBJECT media ON att.ZMEDIA = media.Z_PK
                        WHERE att.ZIDENTIFIER = ?
                    """, (attachment_id,))

                    row = cursor.fetchone()
                    if row:
                        att_uuid, uti, filename, filesize, media_uuid = row

                        # Read media file from filesystem using the media UUID
                        media_result = self._read_media_file(media_uuid) if media_uuid else None

                        if media_result:
                            media_data, discovered_filename = media_result

                            # Determine filename (prefer database filename, then discovered, then generated)
                            final_filename = filename or discovered_filename
                            if not final_filename:
                                # Generate filename from UTI if no filename available
                                ext = self._get_extension_from_uti(uti or type_uti)
                                final_filename = f"{att_uuid[:8]}{ext}"

                            attachments.append({
                                'uuid': att_uuid,
                                'type_uti': uti or type_uti,
                                'filename': final_filename,
                                'data': media_data,
                                'position': pos
                            })

                pos += attr_run.length

        except Exception as e:
            # If attachment extraction fails, continue without attachments
            pass

        return attachments

    def _read_media_file(self, uuid: str) -> Optional[tuple[bytes, str]]:
        """Read media file from filesystem.

        The media files are stored in a nested structure:
        Accounts/<account_uuid>/Media/<media_uuid>/<version_uuid>/<filename>

        Args:
            uuid: UUID of the media record.

        Returns:
            Tuple of (file_data, filename) or None if not found.
        """
        try:
            # Find the account directory (should be only one, but check all)
            if not self.media_base.exists():
                return None

            for account_dir in self.media_base.iterdir():
                if account_dir.is_dir():
                    media_dir = account_dir / "Media" / uuid
                    if media_dir.exists() and media_dir.is_dir():
                        # Media directory contains version subdirectories
                        # Get the first (and usually only) version directory
                        version_dirs = [d for d in media_dir.iterdir() if d.is_dir()]
                        if version_dirs:
                            # Get the first file in the version directory
                            version_dir = version_dirs[0]
                            files = [f for f in version_dir.iterdir() if f.is_file()]
                            if files:
                                file_path = files[0]
                                return (file_path.read_bytes(), file_path.name)

            return None
        except Exception:
            return None

    def _get_extension_from_uti(self, uti: str) -> str:
        """Get file extension from UTI type.

        Args:
            uti: Uniform Type Identifier.

        Returns:
            File extension including dot.
        """
        uti_map = {
            'public.jpeg': '.jpg',
            'public.png': '.png',
            'public.heic': '.heic',
            'public.heif': '.heif',
            'com.apple.image': '.jpg',
            'com.adobe.pdf': '.pdf',
            'public.movie': '.mov',
            'com.apple.quicktime-movie': '.mov',
            'public.mpeg-4': '.mp4',
        }

        for key, ext in uti_map.items():
            if key in uti.lower():
                return ext

        return '.bin'

    def _extract_text_strings(self, data: bytes) -> str:
        """Extract printable text strings from binary protobuf data.

        Args:
            data: Decompressed protobuf binary data.

        Returns:
            Extracted text.
        """
        import re

        # Find all sequences of printable characters
        # Look for strings of at least 3 characters
        strings = []
        current_string = []

        for byte in data:
            char = chr(byte)
            # Include letters, numbers, spaces, and common punctuation
            if char.isprintable() or char in '\n\r\t':
                current_string.append(char)
            else:
                # End of string
                if len(current_string) >= 3:
                    text = ''.join(current_string).strip()
                    if text and not self._is_junk_string(text):
                        strings.append(text)
                current_string = []

        # Don't forget the last string
        if len(current_string) >= 3:
            text = ''.join(current_string).strip()
            if text and not self._is_junk_string(text):
                strings.append(text)

        # Join all valid strings with newlines to preserve structure
        if strings:
            # Filter out very short strings that are likely metadata
            meaningful_strings = [s for s in strings if len(s) > 10]

            # If we filtered out too much, fall back to all strings
            if not meaningful_strings:
                meaningful_strings = strings

            # Join with newlines to preserve note structure
            full_text = '\n\n'.join(meaningful_strings)

            # Post-process to clean up common issues
            full_text = self._cleanup_extracted_text(full_text)

            return full_text

        return ""

    def _cleanup_extracted_text(self, text: str) -> str:
        """Clean up extracted text by removing trailing junk sections.

        Args:
            text: Extracted text.

        Returns:
            Cleaned text.
        """
        import re

        # Split into lines
        lines = text.split('\n')

        # Find where the junk starts - typically after the last URL or meaningful content
        # Look for patterns that indicate junk metadata
        junk_indicators = [
            r'^[ÛØ¨ø½±¬Âßúà£â]{3,}',  # Lines with lots of special chars
            r'^bT$',  # Metadata marker
            r'^\$[0-9A-F]{8}-[0-9A-F]{4}',  # UUID patterns
            r'^com\.apple\.',  # Apple internal identifiers
        ]

        # Scan backwards to find the first occurrence of junk
        # Once we find junk, everything after it is also junk
        first_junk_line = len(lines)

        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()

            if not line:  # Skip empty lines
                continue

            # Check if this line looks like junk
            is_junk = False
            for pattern in junk_indicators:
                if re.match(pattern, line):
                    is_junk = True
                    break

            # Check for high density of special characters
            # A line is junk if it has LOTS of these chars AND is mostly these chars
            if not is_junk and line:
                special_count = sum(c in 'ÛØ¨ø½±¬ÂßúÃ£â' for c in line)
                # Only mark as junk if >70% special AND has at least 5 special chars
                if special_count >= 5 and special_count > len(line) * 0.7:
                    is_junk = True

            if is_junk:
                first_junk_line = i

        # Keep only lines before the junk starts
        cleaned_lines = lines[:first_junk_line]

        return '\n'.join(cleaned_lines).strip()

    def _is_junk_string(self, text: str) -> bool:
        """Check if a string is likely junk/metadata rather than content.

        Args:
            text: String to check.

        Returns:
            True if string appears to be junk.
        """
        # Filter out strings that are mostly non-alphanumeric
        alphanumeric_count = sum(c.isalnum() or c.isspace() for c in text)
        if len(text) > 0 and alphanumeric_count / len(text) < 0.5:
            return True

        # Filter out hex-like strings (but allow if they have spaces, likely content)
        if all(c in '0123456789abcdefABCDEF-' for c in text.replace(' ', '').replace('\n', '')):
            return True

        # Filter out Apple Notes metadata patterns
        junk_patterns = [
            'com.apple.notes',
            'inlinetextattachment',
            'UTI-Data',
            'public.url',
            'attributerun',
            'NSMutableString',
        ]
        if any(pattern in text for pattern in junk_patterns):
            return True

        # Filter out strings with too many repeated special characters
        special_chars = sum(c in 'ÛØ¨ø½±¬ÂßúÃ£â' for c in text)
        if len(text) > 0 and special_chars / len(text) > 0.3:
            return True

        # Filter out very short strings with mostly punctuation
        if len(text) < 15:
            punct_count = sum(c in '.,;:!?-_()[]{}' for c in text)
            if punct_count / len(text) > 0.5:
                return True

        return False

    def _convert_apple_timestamp(self, timestamp: Optional[float]) -> Optional[datetime]:
        """Convert Apple's timestamp format to datetime.

        Apple uses seconds since 2001-01-01 00:00:00 UTC.

        Args:
            timestamp: Apple timestamp.

        Returns:
            datetime object or None.
        """
        if timestamp is None:
            return None

        try:
            # Apple's epoch is 2001-01-01, Unix epoch is 1970-01-01
            # Difference is 978307200 seconds
            unix_timestamp = timestamp + 978307200
            return datetime.fromtimestamp(unix_timestamp)
        except (ValueError, OSError):
            return None
