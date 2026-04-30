#!/usr/bin/env python3
"""Interactively edit ID3 metadata for mp3 files in a folder.

For each file the script walks every common tag field, pre-filling the prompt
with the existing value so it can be edited in place. Files where title,
artist, and album are all empty are flagged before the prompts begin.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from mutagen.easyid3 import EasyID3
    from mutagen.id3 import ID3NoHeaderError
    from mutagen.mp3 import MP3
except ImportError:
    sys.exit("missing dependency: pip install mutagen")

try:
    from prompt_toolkit import prompt as pt_prompt
    HAS_PT = True
except ImportError:
    HAS_PT = False


FIELDS = [
    ("title", "Title"),
    ("artist", "Artist"),
    ("album", "Album"),
    ("albumartist", "Album artist"),
    ("date", "Year"),
    ("tracknumber", "Track"),
    ("genre", "Genre"),
]


def ask(label: str, default: str) -> str:
    if HAS_PT:
        return pt_prompt(f"{label}: ", default=default).strip()
    if default:
        print(f"  current {label}: {default!r}")
        ans = input(f"  new {label} (Enter to keep): ").strip()
        return ans if ans else default
    return input(f"  {label}: ").strip()


def get(tags, key: str) -> str:
    val = tags.get(key)
    if not val:
        return ""
    return val[0] if isinstance(val, list) else str(val)


def load_tags(path: Path) -> EasyID3:
    try:
        return EasyID3(path)
    except ID3NoHeaderError:
        mp3 = MP3(path)
        mp3.add_tags()
        mp3.save()
        return EasyID3(path)


def is_blank(path: Path) -> bool:
    try:
        tags = EasyID3(path)
    except ID3NoHeaderError:
        return True
    return not (get(tags, "title") or get(tags, "artist") or get(tags, "album"))


def edit_file(path: Path) -> None:
    print(f"\n=== {path.name} ===")
    tags = load_tags(path)

    current = {key: get(tags, key) for key, _ in FIELDS}
    if not current["title"] and not current["artist"] and not current["album"]:
        print("  (no title, artist, or album set)")

    changed = False
    for key, label in FIELDS:
        new = ask(label, current[key])
        if new != current[key]:
            if new:
                tags[key] = [new]
            elif key in tags:
                del tags[key]
            changed = True

    if changed:
        tags.save()
        print("  saved.")
    else:
        print("  no changes.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Walk every mp3 in a folder and edit its ID3 tags interactively."
    )
    parser.add_argument(
        "--folder", "-f", type=Path,
        default=Path.home() / "Music" / "mus11",
        help="folder of mp3 files (default: ~/Music/mus11)",
    )
    parser.add_argument(
        "--recursive", "-r", action="store_true",
        help="recurse into subfolders",
    )
    parser.add_argument(
        "--missing-only", action="store_true",
        help="only prompt for files where title, artist, and album are all empty",
    )
    args = parser.parse_args()

    if not args.folder.is_dir():
        print(f"folder not found: {args.folder}", file=sys.stderr)
        return 1

    pattern = "**/*.mp3" if args.recursive else "*.mp3"
    files = sorted(p for p in args.folder.glob(pattern) if p.is_file())
    if not files:
        print(f"no mp3 files in {args.folder}")
        return 0

    if not HAS_PT:
        print("(tip: pip install prompt_toolkit for in-place editable prompts)")

    for f in files:
        try:
            if args.missing_only and not is_blank(f):
                continue
            edit_file(f)
        except KeyboardInterrupt:
            print("\naborted.")
            return 130
        except Exception as e:
            print(f"  error on {f.name}: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
