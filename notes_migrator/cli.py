"""Command-line interface for the Apple Notes to Notesnook exporter."""

import argparse
import sys
from pathlib import Path

from .apple_notes import AppleNotesExtractor
from .notesnook_export import NotesnookExporter


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

        print(f"\n{'=' * 50}")
        print(f"Export complete!")
        print(f"  ✓ Exported: {successful} notes")
        print(f"  📁 Location: {args.output_dir}")
        print(f"  📎 Attachments reference: {args.attachments_dir}/")
        print(f"{'=' * 50}")

        print("\n📥 To import into Notesnook:")
        print(
            f"1. Place your attachment files in: {args.output_dir}/{args.attachments_dir}/"
        )
        print("2. Open Notesnook app")
        print("3. Go to Settings > Notesnook Importer")
        print("4. Select 'Markdown' as the source")
        print(f"5. Select the folder: {args.output_dir}")
        print("6. Review and confirm the import")
        print("\nNote: Notesnook supports markdown with YAML frontmatter")
        print("including title, created/updated dates, and tags.")

        return 0

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
