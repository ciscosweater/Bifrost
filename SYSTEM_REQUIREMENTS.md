# System Requirements

This document outlines the system requirements and dependencies for Bifrost.

## Operating System

**Linux only** - Bifrost is a Linux-exclusive application and will not work on Windows or macOS due to SLSsteam dependencies.

### Supported Distributions

- **Ubuntu** 18.04+ (recommended)
- **Fedora** 30+
- **Arch Linux**
- **Debian** 10+
- **Manjaro**
- **Linux Mint** 19+

## Required Software

### Python
- **Python 3.8** or higher
- **pip** package manager
- Python development headers (python3-dev on Debian/Ubuntu)

### Desktop Environment
- **X11** or **Wayland** display server
- **Qt6** compatible desktop environment
- Desktop integration support for .desktop files

## System Dependencies

### Core Libraries
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv python3-dev
sudo apt install libgl1-mesa-glx libegl1-mesa libxrandr2
sudo apt install libxss1 libxcursor1 libxcomposite1 libasound2

# Fedora
sudo dnf install python3 python3-venv python3-devel
sudo dnf install mesa-libGL libXrandr libXScrnSaver libXcursor libXcomposite alsa-lib

# Arch Linux
sudo pacman -S python python-venv
sudo pacman -S mesa libxrandr libxsscrnsaver libxcursor libxcomposite alsa-lib
```

### Audio Support (Optional)
For sound effects and audio feedback:

```bash
# Ubuntu/Debian
sudo apt install alsa-utils alsa-base

# Fedora
sudo dnf install alsa-utils

# Arch Linux
sudo pacman -S alsa-utils
```

**Note**: Without audio packages, Bifrost will still function but without sound effects.

### 32-bit Compatibility (SLSsteam Integration)
Some Steam client features require 32-bit library support:

```bash
# Ubuntu/Debian
sudo apt install libc6:i386 libncurses5:i386 libstdc++6:i386
sudo dpkg --add-architecture i386
sudo apt update
sudo apt install libc6:i386 libncurses5:i386 libstdc++6:i386

# Fedora
sudo dnf install glibc.i686 libstdc++.i686

# Arch Linux (multilib must be enabled)
sudo pacman -S lib32-glibc lib32-libstdc++-lib
```

## Hardware Requirements

### Minimum Requirements
- **RAM**: 2 GB
- **Disk Space**: 500 MB (application) + space for downloaded games
- **Graphics**: Any GPU compatible with OpenGL 2.0+
- **Network**: Internet connection for Steam API and downloads

### Recommended
- **RAM**: 4 GB or more
- **Disk Space**: 10 GB+ free space
- **Graphics**: Dedicated GPU for better UI performance
- **Network**: Broadband connection for faster downloads

## Virtual Environment

Bifrost automatically creates and manages its own Python virtual environment:

- Location: `~/.local/share/Bifrost/bin/.venv`
- Python: Uses system Python 3.8+
- Dependencies: Installed from `requirements.txt`

### Manual Virtual Environment Setup
```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## External Tools

Bifrost integrates several external tools:

### DepotDownloaderMod
- **Purpose**: Download Steam depots
- **Size**: ~77 MB
- **Included**: Yes (in release package)

### Steamless
- **Purpose**: DRM unpacking for Windows executables
- **Size**: ~1.3 MB
- **Included**: Yes (Windows executables for cross-platform unpacking)
- **Platform**: Windows .exe files, but runs on Linux via Wine integration

### SLSsteam
- **Purpose**: Steamclient modification for Linux
- **Size**: ~70 KB (setup script)
- **Included**: Yes
- **Note**: Requires 32-bit compatibility libraries

### SLScheevo
- **Purpose**: Achievement generator
- **Included**: Yes (build artifacts)
- **Purpose**: Statistics and achievement manipulation

## Network Requirements

### Ports
- **80/443** (HTTP/HTTPS): For downloading from Steam and GitHub
- **27015-27030**: Steam network ports (if applicable)

### Domains
- `steamcommunity.com` - Steam API and CDN
- `github.com` - Online fixes downloads
- `raw.githubusercontent.com` - Configuration updates

### API Access
Bifrost uses:
- Steam Web API (public)
- No authentication required for basic functionality
- Optional Steam login for achievement generation (SLScheevo)

## Troubleshooting

### "Python 3 not found"
```bash
sudo apt install python3  # Ubuntu/Debian
sudo dnf install python3  # Fedora
sudo pacman -S python     # Arch
```

### "PyQt6 not available"
```bash
# Ensure virtual environment is activated
source ~/.local/share/Bifrost/bin/.venv/bin/activate
pip install PyQt6
```

### "Permission denied" errors
```bash
# Make scripts executable
chmod +x Bifrost
chmod +x create_release.sh
```

### Sound not working
```bash
# Install ALSA utilities
sudo apt install alsa-utils  # Ubuntu/Debian
sudo dnf install alsa-utils  # Fedora

# Check audio device
aplay -l
```

### 32-bit library errors
```bash
# Enable multilib (Arch Linux)
sudo nano /etc/pacman.conf
# Uncomment: [multilib]
# Run: sudo pacman -Syy

# Install 32-bit libraries (see 32-bit Compatibility section above)
```

## Configuration Files

### User Configuration
- **Location**: `~/.config/Bifrost/`
- **Files**:
  - `settings.ini` - Application settings
  - `user.json` - User preferences

### Application Data
- **Location**: `~/.local/share/Bifrost/`
- **Structure**:
  - `bin/` - Application binaries and venv
  - `data/` - Download sessions and cache
  - `backups/` - Game backups
  - `api_cache/` - Steam API cache

## Logs

### Application Logs
- **Development**: `app.log` (in application directory)
- **Production**: `~/.local/share/Bifrost/bin/app.log`

### Viewing Logs
```bash
tail -f ~/.local/share/Bifrost/bin/app.log
```

## Performance Optimization

### Disk I/O
- Use SSD for better download performance
- Ensure sufficient free space (1.5x game size for temporary files)

### Network
- Use wired connection for stability
- Configure QoS to prioritize Steam traffic

### Memory
- Close unused applications during large downloads
- Monitor memory usage: `htop` or `free -h`

## Security Considerations

### Data Storage
- Steam credentials are stored locally (encrypted)
- Download sessions saved in JSON format
- No data transmitted to external servers (except Steam API)

### File Permissions
```bash
# Secure configuration directory
chmod 700 ~/.config/Bifrost
chmod 600 ~/.config/Bifrost/*.ini
```

### Updates
- Always use the latest version
- Verify checksums for manual downloads
- Check GitHub for security advisories

---

## Support

For additional help:
1. Check `app.log` for error messages
2. Verify all dependencies are installed
3. Test with `python main.py --debug`
4. Consult [GitHub Issues](https://github.com/your-repo/bifrost/issues)
