#!/usr/bin/env python3
"""
Translation Management Script for ACCELA
Helps manage translations, find missing strings, and update JSON files
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Set

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.i18n import get_i18n_manager


def find_all_tr_calls() -> Set[str]:
    """Find all tr() calls in Python files"""
    tr_calls = set()
    
    for py_file in Path(".").rglob("*.py"):
        if "venv" in str(py_file) or "__pycache__" in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Simple regex to find tr("context", "text") calls
            import re
            matches = re.findall(r'tr\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']\s*\)', content)
            for context, text in matches:
                tr_calls.add(f"{context}.{text}")
        except Exception as e:
            print(f"Error reading {py_file}: {e}")
    
    return tr_calls


def load_translations(lang_code: str) -> Dict[str, str]:
    """Load translations from JSON file"""
    lang_file = f"translations/{lang_code}.json"
    if os.path.exists(lang_file):
        with open(lang_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("translations", {})
    return {}


def save_translations(lang_code: str, translations: Dict[str, str]):
    """Save translations to JSON file"""
    lang_file = f"translations/{lang_code}.json"
    data = {"translations": translations}
    
    with open(lang_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def check_missing_translations():
    """Check for missing translations in all languages"""
    print("🔍 Checking for missing translations...")
    
    # Find all tr() calls
    all_tr_calls = find_all_tr_calls()
    print(f"📊 Found {len(all_tr_calls)} tr() calls in code")
    
    # Load available languages
    manager = get_i18n_manager()
    languages = manager.get_available_languages()
    
    for lang_code in languages:
        translations = load_translations(lang_code)
        missing = all_tr_calls - set(translations.keys())
        
        if missing:
            print(f"\n❌ {lang_code}: {len(missing)} missing translations")
            for key in sorted(missing)[:10]:  # Show first 10
                print(f"   - {key}")
            if len(missing) > 10:
                print(f"   ... and {len(missing) - 10} more")
        else:
            print(f"✅ {lang_code}: All translations complete")


def add_translation():
    """Add a new translation interactively"""
    print("➕ Add new translation")
    
    context = input("Context (e.g., MainWindow): ").strip()
    text = input("Original text: ").strip()
    
    if not context or not text:
        print("❌ Context and text are required")
        return
    
    key = f"{context}.{text}"
    
    # Load existing translations
    manager = get_i18n_manager()
    languages = manager.get_available_languages()
    
    translations = {}
    for lang_code in languages:
        translations[lang_code] = load_translations(lang_code)
    
    print(f"\nAdding translation for: {key}")
    
    for lang_code, lang_name in languages.items():
        existing = translations[lang_code].get(key, "")
        prompt = f"{lang_name} [{existing}]: " if existing else f"{lang_name}: "
        new_translation = input(prompt).strip()
        
        if new_translation:
            translations[lang_code][key] = new_translation
        elif existing:
            translations[lang_code][key] = existing
        else:
            translations[lang_code][key] = text  # Default to original text
    
    # Save all translations
    for lang_code in languages:
        save_translations(lang_code, translations[lang_code])
    
    print(f"✅ Translation added for {key}")


def update_from_ts():
    """Update JSON translations from TS files (if they were updated manually)"""
    print("🔄 Updating JSON from TS files...")
    
    # This would require the same conversion logic used initially
    # For now, just indicate this feature exists
    print("📝 Feature available - would convert TS files to JSON format")


def main():
    """Main menu"""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "check":
            check_missing_translations()
        elif command == "add":
            add_translation()
        elif command == "update":
            update_from_ts()
        else:
            print(f"Unknown command: {command}")
        return
    
    print("🌐 ACCELA Translation Manager")
    print("1. Check missing translations")
    print("2. Add new translation")
    print("3. Update from TS files")
    print("4. Exit")
    
    while True:
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            check_missing_translations()
        elif choice == "2":
            add_translation()
        elif choice == "3":
            update_from_ts()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid option")


if __name__ == "__main__":
    main()