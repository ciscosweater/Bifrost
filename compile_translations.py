#!/usr/bin/env python3
"""
Simple script to compile .ts translation files to .qm format
"""

import sys
from pathlib import Path


def compile_translations():
    """Compile .ts files to .qm format"""
    translations_dir = Path("translations")

    if not translations_dir.exists():
        print("Translations directory not found")
        return False

    # Find all .ts files
    ts_files = list(translations_dir.glob("*.ts"))

    if not ts_files:
        print("No .ts files found")
        return False

    print(f"Found {len(ts_files)} translation files:")

    for ts_file in ts_files:
        print(f"  - {ts_file.name}")

        # Generate .qm filename
        qm_file = ts_file.with_suffix(".qm")

        # Simple conversion (this is a basic approach)
        try:
            # Read the .ts file
            with open(ts_file, "r", encoding="utf-8") as f:
                f.read()

            # For now, create a placeholder .qm file
            # In a real scenario, you'd use Qt's lrelease tool
            with open(qm_file, "w", encoding="utf-8") as f:
                f.write(f"# Compiled from {ts_file.name}\n")
                f.write(
                    "# This is a placeholder - use Qt Linguist for proper compilation\n"
                )

            print(f"    -> Created {qm_file.name} (placeholder)")

        except Exception as e:
            print(f"    Error processing {ts_file.name}: {e}")
            return False

    print("\nTranslation compilation completed!")
    print(
        "Note: These are placeholder .qm files. For production, use Qt Linguist's lrelease tool."
    )
    return True


if __name__ == "__main__":
    success = compile_translations()
    sys.exit(0 if success else 1)
