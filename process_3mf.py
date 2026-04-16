#!/usr/bin/env python3
"""
3MFresh — strips MakerWorld creator metadata from .3mf files.

Processes all .3mf files found in the input/ directory:
  - Removes the Auxiliaries/ directory (creator thumbnails, model images, etc.)
  - Removes dangling Auxiliaries entries from _rels/.rels to prevent load failures
    in BambuStudio v2.x ("does not contain any geometry data")
  - Strips creator metadata from 3D/3dmodel.model, keeping only the slicer
    application name/version and format version number
  - Removes local source_file paths from Metadata/model_settings.config
  - Removes plate preview images from Metadata/ (they regenerate on next slice)

Compatible with BambuStudio and Orca Slicer .3mf files, which share the same
internal format.
"""

import argparse
import logging
import shutil
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
PROCESSED_BASE = BASE_DIR / "processed"
ORIGINALS_BASE = BASE_DIR / "originals"

# Metadata name= attributes to preserve in 3D/3dmodel.model.
# "Application" retains the slicer name and version (BambuStudio or Orca Slicer).
# "BambuStudio:3mfVersion" is required for slicer compatibility.
# Everything else (designer, title, description, cover images, etc.) is stripped.
METADATA_WHITELIST = (
    '<metadata name="Application"',
    '<metadata name="BambuStudio:3mfVersion"',
)


def process_file(filepath: Path, processed_dir: Path) -> None:
    """Process a single .3mf file and write the result to processed_dir."""
    logging.info(f"Processing: {filepath.name}")

    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)

        # Extract the .3mf (ZIP) contents to a temporary directory.
        with zipfile.ZipFile(filepath, "r") as zf:
            zf.extractall(temp)

        # --- Auxiliaries/ --------------------------------------------------
        # Remove the Auxiliaries/ directory, which holds creator thumbnails,
        # model photos, and assembly guides from the original MakerWorld upload.
        aux_dir = temp / "Auxiliaries"
        if aux_dir.exists():
            shutil.rmtree(aux_dir)
            logging.info("  Removed Auxiliaries/")

            # Remove the now-broken Auxiliaries entries from _rels/.rels.
            # BambuStudio v2.x validates all relationships before loading geometry
            # and raises "does not contain any geometry data" when it finds
            # relationship entries pointing to files that no longer exist.
            rels_file = temp / "_rels" / ".rels"
            if rels_file.exists():
                lines = rels_file.read_text(encoding="utf-8").splitlines(keepends=True)
                rels_file.write_text(
                    "".join(line for line in lines if "/Auxiliaries/" not in line),
                    encoding="utf-8",
                )
                logging.info("  Cleaned _rels/.rels")

        # --- 3D/3dmodel.model ----------------------------------------------
        # Strip creator metadata elements, keeping only whitelisted entries.
        # BambuStudio and Orca Slicer both write each <metadata> on its own
        # line, so line-based filtering is safe and avoids the namespace
        # complexities of reserializing the full XML with ElementTree.
        model_file = temp / "3D" / "3dmodel.model"
        if model_file.exists():
            lines = model_file.read_text(encoding="utf-8").splitlines(keepends=True)
            cleaned = [
                line for line in lines
                if not (
                    line.lstrip().startswith("<metadata")
                    and not any(line.lstrip().startswith(w) for w in METADATA_WHITELIST)
                )
            ]
            model_file.write_text("".join(cleaned), encoding="utf-8")
            removed = len(lines) - len(cleaned)
            logging.info(f"  Stripped {removed} metadata element(s) from 3D/3dmodel.model")

        # --- Metadata/model_settings.config --------------------------------
        # Remove source_file entries, which contain local filesystem paths
        # from whoever last saved the file and serve no purpose in a cleaned file.
        settings_file = temp / "Metadata" / "model_settings.config"
        if settings_file.exists():
            lines = settings_file.read_text(encoding="utf-8").splitlines(keepends=True)
            cleaned = [line for line in lines if 'key="source_file"' not in line]
            if len(cleaned) < len(lines):
                settings_file.write_text("".join(cleaned), encoding="utf-8")
                removed = len(lines) - len(cleaned)
                logging.info(
                    f"  Removed {removed} source_file path(s) from "
                    "Metadata/model_settings.config"
                )

        # --- Metadata/ preview images --------------------------------------
        # Remove plate preview PNGs (plate_N.png, top_N.png, pick_N.png, etc.).
        # These are visual snapshots of the original creator's print plate.
        # They are not needed for slicing and regenerate automatically the
        # next time the file is opened and sliced.
        metadata_dir = temp / "Metadata"
        if metadata_dir.exists():
            images = list(metadata_dir.glob("*.png"))
            for img in images:
                img.unlink()
            if images:
                logging.info(
                    f"  Removed {len(images)} plate preview image(s) from Metadata/"
                )

        # --- Repackage -----------------------------------------------------
        out_path = processed_dir / filepath.name
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as new_zip:
            for file_path in sorted(temp.rglob("*")):
                if file_path.is_file():
                    new_zip.write(file_path, file_path.relative_to(temp))

    logging.info(f"  → {out_path.relative_to(BASE_DIR)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="3MFresh: strip MakerWorld creator metadata from .3mf files.",
        epilog=(
            "Place .3mf files in the input/ directory, then run this script. "
            "Processed files are saved to processed/<timestamp>/ and originals "
            "are moved to originals/<timestamp>/."
        ),
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="suppress per-file detail; show only errors and the final summary",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(message)s",
    )

    INPUT_DIR.mkdir(exist_ok=True)

    candidates = sorted(INPUT_DIR.iterdir())
    files = [f for f in candidates if f.suffix.lower() == ".3mf"]
    others = [
        f for f in candidates
        if f.suffix.lower() != ".3mf" and not f.name.startswith(".")
    ]

    for f in others:
        logging.warning(f"Skipping (not a .3mf file): {f.name}")

    if not files:
        print("No .3mf files found in input/. Nothing to do.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    processed_dir = PROCESSED_BASE / timestamp
    originals_dir = ORIGINALS_BASE / timestamp
    processed_dir.mkdir(parents=True, exist_ok=True)
    originals_dir.mkdir(parents=True, exist_ok=True)

    processed, failed = 0, 0

    for filepath in files:
        try:
            if not zipfile.is_zipfile(filepath):
                raise zipfile.BadZipFile(f"{filepath.name} is not a valid ZIP/3MF file")
            process_file(filepath, processed_dir)
            shutil.move(filepath, originals_dir / filepath.name)
            processed += 1
        except zipfile.BadZipFile as e:
            logging.error(f"ERROR: {e} — skipped.")
            failed += 1
        except Exception as e:
            logging.error(f"ERROR processing {filepath.name}: {e} — skipped.")
            failed += 1

    parts = [f"{processed} file{'s' if processed != 1 else ''} processed"]
    if failed:
        parts.append(f"{failed} failed")
    print(f"\nDone. {', '.join(parts)}.")
    if processed:
        print(f"Processed files → {processed_dir.relative_to(BASE_DIR)}/")


if __name__ == "__main__":
    main()
