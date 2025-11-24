# Changelog

All notable changes to Bifrost will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Future changes will be documented here

## [1.1.1] - 2025-11-24

### Added
- CREDITS.md included in release package
- Translation management script (manage_translations.py) with check, add, and update commands
- Complete Portuguese (pt_BR) translation support
- JSON-based internationalization system with English and Portuguese support

### Changed
- Refactored translation system from Qt .ts/.qm files to JSON-based system
- Improved logo scaling to maintain aspect ratio in main window
- Standardized on MotivaSans font for consistent typography
- Updated .gitignore coverage for better development workflow

### Fixed
- Fixed Steamless integration path conversion and execution
- Corrected game deletion path traversal vulnerability
- Fixed DepotDownloaderMod path handling
- Resolved various UI scaling and display issues

### Technical
- Modern PyQt6-based interface with dark theme
- Integrated Steam API for depot information
- Automated virtual environment setup
- Comprehensive logging and error handling
- Modular architecture with clear separation of concerns

## [1.1.0] - Previous Release

### Added
- Initial release with core depot downloading functionality
- Steamless DRM unpacker integration
- SLSsteam and SLScheevo support for Linux
- Game management and backup features
- Online fixes manager for GitHub integration
- Download speed monitoring
- ZIP file processing capabilities

### Features
- PyQt6 graphical interface
- Modern dark theme
- Sound effects and visual feedback
- Desktop integration with .desktop files
- Automatic dependency management
- Progress tracking and notifications

---

## Version History

**Bifrost** is a continued evolution of the original **ACCELA** project, maintaining the same core functionality while introducing improvements and refinements.

### Supported Platforms
- Linux (Ubuntu, Arch, Fedora, etc.)
- Python 3.8+
- PyQt6

### External Dependencies
- DepotDownloaderMod - Main depot downloading tool
- Steamless - DRM unpacker for Windows executables
- SLSsteam - Steamclient modification for Linux
- SLScheevo - Achievement generator
