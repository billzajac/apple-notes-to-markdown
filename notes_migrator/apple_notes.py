"""Extract notes from Apple Notes database."""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AppleNote:
    """Represents a note extracted from Apple Notes."""

    title: str
    content: str
    created_date: Optional[datetime]
    modified_date: Optional[datetime]
    folder: Optional[str]


class AppleNotesExtractor:
    """Extracts notes from the Apple Notes SQLite database."""

    DEFAULT_DB_PATH = Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize extractor with database path.

        Args:
            db_path: Path to Notes database. Uses default location if None.
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH

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
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()

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
                    c.ZDATA as content_data
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
                pk, title, snippet, created, modified, folder, content_data = row

                # Extract text content from binary data
                content = self._extract_content(content_data, snippet)

                # Convert Apple's time format (seconds since 2001-01-01)
                created_date = self._convert_apple_timestamp(created)
                modified_date = self._convert_apple_timestamp(modified)

                note = AppleNote(
                    title=title or "Untitled",
                    content=content,
                    created_date=created_date,
                    modified_date=modified_date,
                    folder=folder
                )
                notes.append(note)

            conn.close()

        except sqlite3.Error as e:
            raise RuntimeError(f"Failed to read Apple Notes database: {e}")

        return notes

    def _extract_content(self, content_data: Optional[bytes], snippet: Optional[str]) -> str:
        """Extract readable text from note content data.

        Args:
            content_data: Binary content data from database.
            snippet: Text snippet as fallback.

        Returns:
            Extracted text content.
        """
        if not content_data:
            return snippet or ""

        try:
            # Apple Notes content is stored as a binary plist with protobuf data
            # For simplicity, we'll extract UTF-8 text fragments
            text = content_data.decode('utf-8', errors='ignore')

            # Remove null bytes and clean up
            text = text.replace('\x00', '').strip()

            # If extraction fails, fall back to snippet
            if not text or len(text) < 10:
                return snippet or ""

            return text

        except Exception:
            return snippet or ""

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
