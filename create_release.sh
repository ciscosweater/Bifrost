#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
cd "$SCRIPT_DIR"

RELEASE_DIR="release/Bifrost-RELEASE"
BIN_DIR="$RELEASE_DIR/bin"

echo "Creating Bifrost release..."

# Clean previous release
rm -rf "$RELEASE_DIR"
mkdir -p "$BIN_DIR"

# Copy essential files
echo "Copying essential files..."
cp main.py "$BIN_DIR/"
cp Bifrost "$BIN_DIR/"
cp requirements.txt "$BIN_DIR/"
cp bifrost.png "$BIN_DIR/"
cp LICENSE "$BIN_DIR/"
cp README.md "$BIN_DIR/"
cp CREDITS.md "$BIN_DIR/"
cp CHANGELOG.md "$BIN_DIR/"
cp SYSTEM_REQUIREMENTS.md "$BIN_DIR/"

# Copy essential directories
echo "Copying directories..."
cp -r core "$BIN_DIR/"
cp -r ui "$BIN_DIR/"
cp -r utils "$BIN_DIR/"
cp -r assets "$BIN_DIR/"
cp -r external "$BIN_DIR/"
cp -r translations "$BIN_DIR/"
cp -r config "$BIN_DIR/"
cp -r slscheevo_build "$BIN_DIR/"
cp -r Steamless "$BIN_DIR/"
cp -r SLSsteam-Any "$BIN_DIR/"

# Clean development files
echo "Cleaning development files..."
find "$BIN_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$BIN_DIR" -name "*.pyc" -delete 2>/dev/null || true
find "$BIN_DIR" -name ".gitignore" -delete 2>/dev/null || true
find "$BIN_DIR" -name ".part" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.log" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.tmp" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.temp" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.acf" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.manifest" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.depot" -delete 2>/dev/null || true
find "$BIN_DIR" -name ".DS_Store" -delete 2>/dev/null || true
find "$BIN_DIR" -name "Thumbs.db" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.swp" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.swo" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*~" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.bak" -delete 2>/dev/null || true
find "$BIN_DIR" -name "*.backup" -delete 2>/dev/null || true
rm -rf "$BIN_DIR/api_cache" 2>/dev/null || true
rm -rf "$BIN_DIR/data/sessions" 2>/dev/null || true
rm -rf "$BIN_DIR/Steamless/GLCache" 2>/dev/null || true
rm -rf "$BIN_DIR/backups" 2>/dev/null || true
rm -rf "$BIN_DIR/tmp" 2>/dev/null || true
rm -rf "$BIN_DIR/temp" 2>/dev/null || true
rm -f "$BIN_DIR/slscheevo_build/data/saved_logins.encrypted" 2>/dev/null || true

# Create adapted INSTALL script
echo "Creating INSTALL script..."
cat > "$RELEASE_DIR/INSTALL" << 'EOF'
#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
cd "$SCRIPT_DIR"

INSTALL_DIR="$HOME/.local/share/Bifrost"
BIN_DIR="$INSTALL_DIR/bin"
VENV_DIR="$BIN_DIR/.venv"

cat << "BANNER"
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣶⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠻⠿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠀⠀⠀⠀⢀⣠⣴⣶⣿⣿⣿⣿⣿⣶⣦⣄⡀⠀⠀⠀⠀⣀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⣿⡆⠀⢀⣴⣿⣿⣿⣿⠿⠟⠛⠛⠛⠻⠿⣿⣿⣿⣿⣦⡀⠀⢰⣿⣿⣷⣄⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⣿⠟⠉⠀⣴⣿⣿⣿⠟⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠻⣿⣿⣿⣦⠀⠉⠻⢿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣴⣿⣿⡿⠋⠀⠀⠀⣼⣿⣿⡿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⢿⣿⣿⣧⠀⠀⠀⠙⢿⣿⣿⣦⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣰⣿⣿⡿⠉⠀⠀⠀⠀⢰⣿⣿⣿⠁⠀⠀⠀⠀⣤⣾⣿⣿⣿⣷⣦⠀⠀⠀⠀⠈⣿⣿⣿⡆⠀⠀⠀⠀⠈⠻⣿⣿⣦⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣼⣿⡿⡏⠀⠀⠀⠀⠀⠀⣼⣿⣿⡏⠀⠀⠀⠀⣼⣿⣿⣿⣿⣿⣿⣿⣷⠀⠀⠀⠀⢸⣿⣿⣷⠀⠀⠀⠀⠀⠀⢹⣿⣿⣧⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⡇⠀⠀⠀⠀⠀⠀⢿⣿⣿⡇⠀⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⠀⠀⠀⠀⢸⣿⣿⣿⠀⠀⠀⠀⠀⠀⢠⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⣿⣿⣷⡄⠀⠀⠀⠀⠀⢸⣿⣿⣷⠀⠀⠀⠀⠘⢿⣿⣿⣿⣿⣿⡿⠃⠀⠀⠀⠀⣼⣿⣿⡏⠀⠀⠀⠀⠀⢀⣾⣿⣿⠏⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣦⣄⠀⠀⠀⠀⢿⣿⣿⣇⠀⠀⠀⠀⠀⠉⠛⠛⠛⠉⠀⠀⠀⠀⠀⣸⣿⣿⣿⠁⠀⠀⠀⣠⣴⣿⣿⠟⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣷⣤⡀⠀⠘⢿⣿⣿⣷⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣾⣿⣿⡿⠃⠀⢀⣠⣾⣿⣿⠿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣠⣤⡀⠈⠻⢿⣿⣿⣶⠀⠀⠻⣿⣿⣿⣷⣦⣄⠀⠀⠀⠀⠀⣠⣤⣾⣿⣿⡿⠏⠁⠀⣴⣿⣿⣿⠟⠉⢀⣤⣄⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠘⢿⢿⠇⠀⠀⠀⠉⠛⠛⠀⠀⠀⠈⠙⠿⣿⣿⣿⣷⠀⠀⠀⣾⣿⣿⣿⠿⠁⠀⠀⠀⠀⠙⠛⠋⠀⠀⠀⠸⣿⣿⠇⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⣿⣿⣿⠀⠀⠀⣿⣿⣿⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⠀⠀⠀⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⣿⠀⠀⠀⣿⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢰⣵⣷⣄⠀⠀⠀⠀⠀⢀⣿⣿⣿⠀⠀⠀⣿⣿⣿⡄⠀⠀⠀⠀⠀⣠⣾⣷⡆⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠻⣿⣿⣷⣦⣄⣀⣤⣾⣿⡿⠋⠀⠀⠀⠘⣿⣿⣷⣤⣀⣠⣤⣾⣿⡿⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠙⠻⠿⣿⣿⡟⠛⠁⠀⠀⠀⠀⠀⠀⠈⠘⠿⢿⣿⣿⠻⠏⠉⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
BANNER

perform_update() {
    echo "Existing Bifrost installation found. Updating..."

    if [ -f "$BIN_DIR/app.log" ];
    then
        echo "Backing up old log file to app.log.bak..."
        mkdir -p "$INSTALL_DIR"
        mv "$BIN_DIR/app.log" "$INSTALL_DIR/app.log.bak"
    fi

    echo "Removing old application files..."
    rm -rf "$BIN_DIR"
}

if [ -d "$BIN_DIR" ];
then
    perform_update
else
    echo "Starting new Bifrost installation..."
fi

mkdir -p "$INSTALL_DIR"
echo "Installing new application files..."
mv "$SCRIPT_DIR/bin" "$INSTALL_DIR/"
cd "$INSTALL_DIR"

echo "Setting up virtual environment..."
python3 -m venv "$VENV_DIR"

echo "Installing dependencies..."
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$BIN_DIR/requirements.txt"

notify-send "ＥＮＴＥＲＩＮＧ   ＴＨＥ   ＷＩＲＥＤ"

deactivate
echo "Dependencies installed."

DESKTOP_ENTRY_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_ENTRY_DIR"

ICON_THEME_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_THEME_DIR"
install -Dm644 "$BIN_DIR/bifrost.png" "$ICON_THEME_DIR/bifrost.png"

cat > "$DESKTOP_ENTRY_DIR/bifrost.desktop" <<DESKTOP
[Desktop Entry]
Version=2.0
Name=Bifrost
Comment=ＧｏＤ_Ｉｓ_ｉＮ_ｔＨｅ_ＷｉＲｅＤ
Exec=$BIN_DIR/Bifrost
Path=$BIN_DIR/
Icon=bifrost
Terminal=false
Type=Application
Categories=Utility;Application;
DESKTOP

if command -v gtk-update-icon-cache &> /dev/null;
then
    gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" || true
fi
if command -v gtk4-update-icon-cache &> /dev/null; then
    gtk4-update-icon-cache "$HOME/.local/share/icons/hicolor" || true
fi

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications"
fi

chmod -R 777 "$BIN_DIR"
echo "Installation complete!"
EOF

chmod +x "$RELEASE_DIR/INSTALL"

# Create release archive
echo "Creating release archive..."
cd release
RELEASE_FILE="Bifrost-RELEASE-v1.1.1.tar.gz"
tar -czf "$RELEASE_FILE" Bifrost-RELEASE/

echo "Release created: release/$RELEASE_FILE"
echo "Release size: $(du -h "$RELEASE_FILE" | cut -f1)"
echo ""
echo "To install: extract the archive and run ./INSTALL"