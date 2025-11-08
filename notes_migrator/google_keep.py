"""Load notes into Google Keep."""

import gkeepapi
from typing import List, Optional
from .apple_notes import AppleNote


class GoogleKeepLoader:
    """Loads notes into Google Keep."""

    def __init__(self):
        """Initialize the Keep loader."""
        self.keep = gkeepapi.Keep()
        self._authenticated = False

    def login(self, username: str, password: str) -> None:
        """Authenticate with Google Keep.

        Args:
            username: Google account email.
            password: Google account password or app-specific password.

        Raises:
            LoginException: If authentication fails.
        """
        try:
            self.keep.login(username, password)
            self._authenticated = True
        except gkeepapi.exception.LoginException as e:
            raise RuntimeError(
                f"Failed to login to Google Keep: {e}\n"
                "Note: You may need to use an app-specific password if you have 2FA enabled.\n"
                "Generate one at: https://myaccount.google.com/apppasswords"
            )

    def login_with_token(self, username: str, token: str) -> None:
        """Authenticate with Google Keep using a master token.

        Args:
            username: Google account email.
            token: Master token from previous login.

        Raises:
            LoginException: If authentication fails.
        """
        try:
            self.keep.resume(username, token)
            self._authenticated = True
        except gkeepapi.exception.LoginException as e:
            raise RuntimeError(f"Failed to resume Google Keep session: {e}")

    def get_master_token(self) -> str:
        """Get the master token for future logins.

        Returns:
            Master token string.

        Raises:
            RuntimeError: If not authenticated.
        """
        if not self._authenticated:
            raise RuntimeError("Must be authenticated to get master token")

        return self.keep.getMasterToken()

    def create_note(self, apple_note: AppleNote, label: Optional[str] = None) -> gkeepapi.node.Note:
        """Create a note in Google Keep from an Apple Note.

        Args:
            apple_note: The Apple Note to migrate.
            label: Optional label to apply to the note.

        Returns:
            The created Keep note.

        Raises:
            RuntimeError: If not authenticated.
        """
        if not self._authenticated:
            raise RuntimeError("Must be authenticated to create notes")

        # Create the note
        note = self.keep.createNote(apple_note.title, apple_note.content)

        # Set timestamps if available
        if apple_note.created_date:
            note.timestamps.created = apple_note.created_date
        if apple_note.modified_date:
            note.timestamps.edited = apple_note.modified_date

        # Add label for the folder if it exists
        if apple_note.folder:
            label_obj = self._get_or_create_label(apple_note.folder)
            note.labels.add(label_obj)

        # Add migration label if specified
        if label:
            label_obj = self._get_or_create_label(label)
            note.labels.add(label_obj)

        return note

    def migrate_notes(
        self,
        notes: List[AppleNote],
        dry_run: bool = False,
        migration_label: str = "Migrated from Apple Notes"
    ) -> tuple[int, int]:
        """Migrate multiple notes to Google Keep.

        Args:
            notes: List of Apple Notes to migrate.
            dry_run: If True, don't actually create notes.
            migration_label: Label to apply to all migrated notes.

        Returns:
            Tuple of (successful_count, failed_count).
        """
        if not self._authenticated:
            raise RuntimeError("Must be authenticated to migrate notes")

        successful = 0
        failed = 0

        for note in notes:
            try:
                if not dry_run:
                    self.create_note(note, label=migration_label)
                successful += 1
                print(f"✓ Migrated: {note.title}")
            except Exception as e:
                failed += 1
                print(f"✗ Failed to migrate '{note.title}': {e}")

        # Sync all changes to Google Keep
        if not dry_run:
            try:
                self.keep.sync()
            except Exception as e:
                print(f"Warning: Failed to sync with Google Keep: {e}")

        return successful, failed

    def _get_or_create_label(self, name: str) -> gkeepapi.node.Label:
        """Get existing label or create new one.

        Args:
            name: Label name.

        Returns:
            Label object.
        """
        # Try to find existing label
        label = self.keep.findLabel(name)

        if label is None:
            # Create new label
            label = self.keep.createLabel(name)

        return label
