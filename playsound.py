#!/usr/bin/env python3
"""
Enhanced sound player for Bifrost with error handling and fallback support
"""

import sys
import time
import os
from pathlib import Path

def try_pygame(sound_file):
    """Try to play sound using pygame"""
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(sound_file)
        pygame.mixer.music.play()
        
        # Wait for music to finish playing
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        return True
    except Exception as e:
        print(f"PyAudio playback failed: {e}", file=sys.stderr)
        return False

def try_system_player(sound_file):
    """Try to play sound using system player"""
    try:
        import subprocess
        import platform
        
        if platform.system() == "Linux":
            # Try different Linux audio players
            players = ["aplay", "paplay", "mpg123", "ffplay"]
            for player in players:
                try:
                    subprocess.run([player, sound_file], check=True, 
                                 capture_output=True, timeout=30)
                    return True
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
        return False
    except Exception:
        return False

def main():
    """Main sound playback function"""
    if len(sys.argv) != 2:
        print("Usage: python playsound.py <sound_file>", file=sys.stderr)
        sys.exit(1)
    
    sound_file = sys.argv[1]
    
    # Validate file exists
    if not os.path.exists(sound_file):
        print(f"Error: Sound file '{sound_file}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Try pygame first (most reliable)
    if try_pygame(sound_file):
        sys.exit(0)
    
    # Fallback to system player
    if try_system_player(sound_file):
        sys.exit(0)
    
    # If all methods fail
    print("Warning: Could not play sound file", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()