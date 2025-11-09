"""Command-line interface for the Apple Notes to Notesnook exporter."""

import argparse
import sys
import os
from pathlib import Path

from .apple_notes import AppleNotesExtractor
from .notesnook_export import NotesnookExporter


def check_permissions():
    """Check if the user has necessary permissions to access Apple Notes."""
    print("🔐 Checking permissions for Apple Notes access...\n")

    db_path = Path.home() / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
    media_base = Path.home() / "Library/Group Containers/group.com.apple.notes/Accounts"

    all_ok = True

    # Check database access
    print(f"📁 Database location: {db_path}")
    if not db_path.exists():
        print("   ❌ Database not found")
        print("   → Make sure Apple Notes has been opened at least once")
        all_ok = False
    elif not os.access(db_path, os.R_OK):
        print("   ❌ Cannot read database (permission denied)")
        all_ok = False
    else:
        print("   ✅ Database accessible")
        # Try to actually open it
        try:
            import sqlite3
            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ZICCLOUDSYNCINGOBJECT WHERE ZTITLE1 IS NOT NULL")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"   ✅ Can read database ({count} note objects found)")
        except Exception as e:
            print(f"   ❌ Error reading database: {e}")
            all_ok = False

    # Check media directory access
    print(f"\n📁 Media location: {media_base}")
    if not media_base.exists():
        print("   ⚠️  Media directory not found (no attachments will be extracted)")
    elif not os.access(media_base, os.R_OK):
        print("   ❌ Cannot read media directory (permission denied)")
        all_ok = False
    else:
        print("   ✅ Media directory accessible")
        # Check if we can list accounts
        try:
            accounts = [d for d in media_base.iterdir() if d.is_dir()]
            if accounts:
                print(f"   ✅ Found {len(accounts)} account(s)")
                for account in accounts:
                    media_dir = account / "Media"
                    if media_dir.exists():
                        media_count = len([f for f in media_dir.iterdir()])
                        print(f"   ✅ {media_count} media files in {account.name[:8]}...")
            else:
                print("   ⚠️  No accounts found")
        except Exception as e:
            print(f"   ❌ Error reading media directory: {e}")
            all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All permissions OK! You can run notes-export successfully.")
        print("=" * 60)
        return 0
    else:
        print("❌ Permission issues detected!")
        print("=" * 60)
        print("\n📋 To fix permission issues:")
        print("1. Open System Settings → Privacy & Security → Full Disk Access")
        print("2. Click the '+' button and add your terminal application:")
        print("   - Terminal.app: /Applications/Utilities/Terminal.app")
        print("   - iTerm.app: /Applications/iTerm.app")
        print("   - Or your preferred terminal app")
        print("3. Toggle the switch ON for your terminal")
        print("4. IMPORTANT: Quit and restart your terminal completely")
        print("5. Run this check again: notes-export --check-permissions")
        print("\nFor more help, see: README.md (Installation section)")
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Export Apple Notes to Notesnook markdown format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all notes to Notesnook markdown format
  notes-migrate

  # Export with custom output directory
  notes-migrate --output-dir ./my-notes

  # Dry run to preview notes without exporting
  notes-migrate --dry-run

  # Export limited number of notes for testing
  notes-migrate --max-notes 10
        """,
    )

    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to Apple Notes database (default: ~/Library/Group Containers/group.com.apple.notes/NoteStore.sqlite)",
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Preview notes without exporting them"
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd() / "my-notes",
        help="Directory for exported markdown files (default: ./my-notes)",
    )

    parser.add_argument(
        "--attachments-dir",
        default="attachments",
        help="Attachments directory name for markdown references (default: attachments)",
    )

    parser.add_argument(
        "--max-notes", type=int, help="Maximum number of notes to export (for testing)"
    )

    parser.add_argument(
        "--check-permissions",
        action="store_true",
        help="Check if you have the necessary permissions to access Apple Notes",
    )

    args = parser.parse_args()

    # Handle permission check mode
    if args.check_permissions:
        return check_permissions()

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
            notes = notes[: args.max_notes]
            print(f"Limiting to first {args.max_notes} notes")

        # Preview notes
        print("\nNotes to export:")
        for i, note in enumerate(notes[:10], 1):
            folder = f" [{note.folder}]" if note.folder else ""
            print(f"  {i}. {note.title}{folder}")

        if len(notes) > 10:
            print(f"  ... and {len(notes) - 10} more")

        if args.dry_run:
            print("\n🔍 Dry run complete. No notes were exported.")
            return 0

        # Export to Notesnook
        print(f"\n📝 Exporting notes to Notesnook markdown format...")
        print(f"Output directory: {args.output_dir}")

        exporter = NotesnookExporter()
        successful = exporter.export_notes(notes, args.output_dir, args.attachments_dir)

        # Count attachments
        attachment_count = 0
        attachments_path = args.output_dir / args.attachments_dir
        if attachments_path.exists():
            attachment_count = len([f for f in attachments_path.iterdir() if f.is_file()])

        print(f"\n{'=' * 60}")
        print(f"✅ Export complete!")
        print(f"  📝 Exported: {successful} notes")
        if attachment_count > 0:
            print(f"  📎 Extracted: {attachment_count} attachments")
        print(f"  📁 Location: {args.output_dir.absolute()}")
        print(f"{'=' * 60}")

        # Create ZIP file automatically
        print(f"\n📦 Creating ZIP file for Notesnook import...")
        import shutil
        zip_path = args.output_dir.parent / f"{args.output_dir.name}"

        try:
            # Create the zip file (without .zip extension, shutil.make_archive adds it)
            zip_file = shutil.make_archive(
                str(zip_path),
                'zip',
                args.output_dir.parent,
                args.output_dir.name
            )
            print(f"  ✅ Created: {zip_file}")

            # Remove the output directory after successful ZIP creation
            shutil.rmtree(args.output_dir)
            print(f"  🗑️  Removed: {args.output_dir}")
        except Exception as e:
            print(f"  ⚠️  Failed to create ZIP: {e}")
            print(f"  You can manually zip the folder: zip -r {args.output_dir.name}.zip {args.output_dir.name}")
            zip_file = None

        print(f"\n{'=' * 60}")
        print(f"📥 To import into Notesnook:")
        if zip_file:
            print(f"1. Open Notesnook app")
            print(f"2. Go to Settings → Notesnook Importer")
            print(f"3. Select 'Markdown' as the source")
            print(f"4. Select the ZIP file: {Path(zip_file).name}")
            print(f"5. Review and confirm the import")
        else:
            print(f"1. Zip the export folder first")
            print(f"2. Open Notesnook app")
            print(f"3. Go to Settings → Notesnook Importer")
            print(f"4. Select 'Markdown' as the source")
            print(f"5. Select the ZIP file or folder")

        print(f"\nℹ️  Exported with YAML frontmatter including:")
        print(f"   • Title, created/updated dates, and tags")
        print(f"   • Images and PDFs embedded with markdown syntax")
        print(f"{'=' * 60}")

        return 0

    except FileNotFoundError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        print("\n💡 This usually means:", file=sys.stderr)
        print("   - Apple Notes database not found on this system", file=sys.stderr)
        print("   - Make sure you're running on macOS with Apple Notes installed", file=sys.stderr)
        print("   - Open Apple Notes at least once to create the database", file=sys.stderr)
        return 1
    except RuntimeError as e:
        print(f"✗ Error: {e}", file=sys.stderr)
        if "Permission denied" in str(e) or "not permitted" in str(e).lower():
            print("\n💡 Permission error detected!", file=sys.stderr)
            print("   Run: notes-export --check-permissions", file=sys.stderr)
            print("   Or see README.md for permission setup instructions", file=sys.stderr)
        return 1
    except PermissionError as e:
        print(f"✗ Permission Error: {e}", file=sys.stderr)
        print("\n💡 You need Full Disk Access for your terminal!", file=sys.stderr)
        print("   1. Run: notes-export --check-permissions", file=sys.stderr)
        print("   2. Follow the instructions to grant Full Disk Access", file=sys.stderr)
        print("   3. Restart your terminal completely", file=sys.stderr)
        print("\n   See README.md Installation section for detailed steps.", file=sys.stderr)
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
