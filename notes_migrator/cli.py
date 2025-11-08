"""Command-line interface for the Apple Notes to Google Keep migrator."""

import sys
import getpass
import argparse
from pathlib import Path
from typing import Optional

from .apple_notes import AppleNotesExtractor
from .google_keep import GoogleKeepLoader


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate Apple Notes to Google Keep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate all notes
  notes-migrate

  # Dry run to preview notes without migrating
  notes-migrate --dry-run

  # Use custom Apple Notes database
  notes-migrate --db-path /path/to/NoteStore.sqlite

  # Use custom label for migrated notes
  notes-migrate --label "Imported from Mac"
        """
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to Apple Notes database (default: ~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview notes without actually migrating them"
    )

    parser.add_argument(
        "--label",
        default="Migrated from Apple Notes",
        help="Label to apply to migrated notes (default: 'Migrated from Apple Notes')"
    )

    parser.add_argument(
        "--username",
        help="Google account email (will prompt if not provided)"
    )

    parser.add_argument(
        "--max-notes",
        type=int,
        help="Maximum number of notes to migrate (for testing)"
    )

    args = parser.parse_args()

    try:
        # Step 1: Extract Apple Notes
        print("📱 Extracting notes from Apple Notes...")
        extractor = AppleNotesExtractor(args.db_path)
        notes = extractor.extract_all_notes()

        if not notes:
            print("No notes found in Apple Notes.")
            return 0

        print(f"Found {len(notes)} notes")

        # Limit notes if specified
        if args.max_notes:
            notes = notes[:args.max_notes]
            print(f"Limiting to first {args.max_notes} notes")

        # Preview notes
        print("\nNotes to migrate:")
        for i, note in enumerate(notes[:10], 1):
            folder = f" [{note.folder}]" if note.folder else ""
            print(f"  {i}. {note.title}{folder}")

        if len(notes) > 10:
            print(f"  ... and {len(notes) - 10} more")

        if args.dry_run:
            print("\n🔍 Dry run complete. No notes were migrated.")
            return 0

        # Step 2: Authenticate with Google Keep
        print("\n🔐 Authenticating with Google Keep...")

        username = args.username
        if not username:
            username = input("Google account email: ")

        password = getpass.getpass("Google password (or app-specific password): ")

        loader = GoogleKeepLoader()

        try:
            loader.login(username, password)
            print("✓ Authenticated successfully")

            # Save master token for future use
            token = loader.get_master_token()
            print(f"\n💡 Tip: Save this token to skip login next time:")
            print(f"   (Token is stored in your system keyring)")

        except RuntimeError as e:
            print(f"✗ Authentication failed: {e}")
            return 1

        # Step 3: Migrate notes
        print(f"\n📤 Migrating {len(notes)} notes to Google Keep...")
        print("This may take a few minutes...\n")

        successful, failed = loader.migrate_notes(
            notes,
            dry_run=False,
            migration_label=args.label
        )

        # Summary
        print(f"\n{'='*50}")
        print(f"Migration complete!")
        print(f"  ✓ Successful: {successful}")
        print(f"  ✗ Failed: {failed}")
        print(f"{'='*50}")

        if successful > 0:
            print("\n✨ Your notes are now available in Google Keep!")
            print("   Check them at: https://keep.google.com")

        return 0 if failed == 0 else 1

    except FileNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        return 130
    except Exception as e:
        print(f"✗ Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
