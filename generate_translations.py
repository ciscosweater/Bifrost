#!/usr/bin/env python3
"""
Generate missing translations automatically
"""

import json
import os
import sys
import re
from pathlib import Path
from typing import Dict, Set

# Add project root to path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


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


def generate_missing_translations():
    """Generate missing translations automatically"""
    print("🔍 Finding all tr() calls...")
    
    # Find all tr() calls
    all_tr_calls = find_all_tr_calls()
    print(f"📊 Found {len(all_tr_calls)} tr() calls in code")
    
    # Load existing translations
    languages = {"en": "English", "pt_BR": "Português (Brasil)"}
    
    for lang_code, lang_name in languages.items():
        print(f"\n🔄 Processing {lang_name} ({lang_code})...")
        
        translations = load_translations(lang_code)
        missing = all_tr_calls - set(translations.keys())
        
        if not missing:
            print(f"✅ All translations complete for {lang_code}")
            continue
        
        print(f"➕ Adding {len(missing)} missing translations...")
        
        for key in sorted(missing):
            if lang_code == "en":
                # For English, use the original text
                original_text = key.split(".", 1)[1]
                translations[key] = original_text
            else:
                # For Portuguese, try to use existing translations or leave as original
                original_text = key.split(".", 1)[1]
                translations[key] = original_text  # Could add auto-translation here
        
        # Save updated translations
        save_translations(lang_code, translations)
        print(f"✅ Saved {len(translations)} translations for {lang_code}")


if __name__ == "__main__":
    generate_missing_translations()