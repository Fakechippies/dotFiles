#!/usr/bin/env bash
set -e

REPO_DIR="$(pwd)"
CONF_DIR="$HOME/.config"
SDDM_THEME_NAME="mycustom"
SDDM_THEME_SRC="$REPO_DIR/sddm/$SDDM_THEME_NAME"
SDDM_THEME_DEST="/usr/share/sddm/themes/$SDDM_THEME_NAME"

echo "==> Installing base packages…"
sudo pacman -S --noconfirm --needed \
    hyprland hyprpaper waybar mako fuzzel ghostty \
    sddm qt5-graphicaleffects qt5-quickcontrols2 \
    grim slurp wl-clipboard swappy

if ! command -v yay &>/dev/null; then
    echo "==> Installing yay (AUR helper)…"
    sudo pacman -S --noconfirm --needed git base-devel
    git clone https://aur.archlinux.org/yay.git /tmp/yay
    cd /tmp/yay
    makepkg -si --noconfirm
    cd -
fi


mkdir -p "$CONF_DIR"

link_config() {
    local name="$1"
    if [ -d "$REPO_DIR/.config/$name" ]; then
        echo "==> Linking $name → ~/.config/$name"
        rm -rf "$CONF_DIR/$name"
        ln -s "$REPO_DIR/.config/$name" "$CONF_DIR/$name"
    fi
}

for cfg in hypr ghostty waybar mako fuzzel starship kitty; do
    link_config "$cfg"
done


if [ -d "$REPO_DIR/wallpapers" ]; then
    echo "==> Copying wallpapers"
    mkdir -p "$HOME/wallpapers"
    cp -r "$REPO_DIR/wallpapers/"* "$HOME/wallpapers/"
fi


echo "==> Installing SDDM theme: $SDDM_THEME_NAME"

sudo mkdir -p "$SDDM_THEME_DEST"
sudo cp -r "$SDDM_THEME_SRC/"* "$SDDM_THEME_DEST/"

sudo touch /etc/sddm.conf

echo "[Theme]
Current=$SDDM_THEME_NAME" | sudo tee /etc/sddm.conf >/dev/null

echo "==> Enabling SDDM service…"
sudo systemctl enable sddm.service

