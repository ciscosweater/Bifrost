# ACCELA - Steam Depot Downloader GUI

Graphical interface for downloading Steam depots with advanced management features.

## Quick Installation

### Linux (Recommended)
```bash
# Run the installation script
chmod +x install_and_setup.sh
./install_and_setup.sh
```

### Manual (Linux)
```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the application
python main.py
```

## Requirements

- **Linux operating system** (Ubuntu, Arch, Fedora, etc.)
- Python 3.8+
- PyQt6
- Internet connection
- 32-bit compatibility libraries (for SLSsteam integration)

## How to Use

1. **Configure your Steam credentials on SLScheevo** (optional, for generating achievements)
2. **Run ACCELA** through installer or manually
3. **Select the desired game** selecting a .zip file containing manifests and .lua
4. **Choose depots/manifests** to download
5. **Set the destination** directory
6. **Start the download** and monitor progress

## Features

- Intuitive PyQt6-based interface
- ZIP file support for processing
- Download speed monitoring
- Installed games management
- Modern dark theme

## File Structure

```
ACCELA Python/
├── main.py              # Main entry point
├── requirements.txt     # Python dependencies
├── install_and_setup.sh # Linux installation script
├── core/               # Core application logic
├── ui/                 # Interface components
├── utils/              # Utilities and helpers
├── config/             # Configuration files
├── external/           # External tools
├── Steamless/          # Steamless tool
└── SLSsteam-Any/       # SLSSteam for variants
```

## Important Notice

This software is intended for educational and personal use. Users are responsible for:
- Respecting Steam Terms of Service
- Only downloading content they legally own
- Not distributing copyrighted content
- **Linux-only application** - Will not work on Windows or macOS due to SLSsteam dependencies

## Security

- Steam credentials are stored locally
- No information is sent to external servers
- Always use the latest application version

## Common Issues

**Application doesn't start**: Check if Python 3.8+ is installed
**Dependency errors**: Run `pip install -r requirements.txt`
**Download failure**: Check connection and Steam credentials

## Support

For issues and suggestions, check the documentation or contact the developer.

## Credits and Acknowledgments

**Original ACCELA**: The original ACCELA project was created by an unknown developer. This repository is a modified and enhanced version that improves the user experience and adds new functionality while maintaining the core purpose.

**Current Maintainer**: This modified version is maintained with improvements to the interface, additional features, and better usability.

This project incorporates open-source third-party tools:

### Included External Tools

- **[DepotDownloader](https://github.com/SteamAutoCracks/DepotDownloaderMod)**
  - Main tool for downloading Steam depots

- **[Steamless](https://github.com/atom0s/Steamless)**
  - Steam DRM executable unpacker
  - Author: atom0s

- **[SLSsteam](https://github.com/AceSLS/SLSsteam)** - Steamclient modification for Linux
  - Author: AceSLS
  - Description: Steamclient modification for enabling special Steam features

- **[SLScheevo](https://github.com/xamionex/SLScheevo)** - Achievement generator for SLSsteam
  - Author: xamionex
  - Description: Achievement generator meant to be used with SLSsteam

### Technologies Used

- **Python 3.8+** - Main language
- **PyQt6** - GUI framework
- **Steam Web API** - Steam services integration

---

**Version**: 1.0
**Developed with**: Python, PyQt6, Steam API
**Platform**: Linux only
**License**: See LICENSE file for details
