#!/usr/bin/env bash
set -euo pipefail

if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "This installer must be run with sudo." >&2
  exit 1
fi

if [ -z "${SUDO_USER:-}" ] || [ "${SUDO_USER}" = "root" ]; then
  echo "Run this installer via sudo from your normal user." >&2
  exit 1
fi

TARGET_USER="$SUDO_USER"
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
if [ -z "$TARGET_HOME" ]; then
  echo "Could not resolve home directory for $TARGET_USER." >&2
  exit 1
fi

TARGET_UID="$(id -u "$TARGET_USER")"
RUNTIME_DIR="/run/user/$TARGET_UID"
if [ ! -d "$RUNTIME_DIR" ]; then
  install -d -m 700 -o "$TARGET_USER" -g "$TARGET_USER" "$RUNTIME_DIR"
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_ROOT="$TARGET_HOME/.config"

run_as_user() {
  runuser -u "$TARGET_USER" -- env HOME="$TARGET_HOME" XDG_CONFIG_HOME="$CONFIG_ROOT" XDG_RUNTIME_DIR="$RUNTIME_DIR" "$@"
}

backup_dir() {
  local target="$1"
  local backup="${target}.bak"
  if [ -e "$target" ] && [ ! -e "$backup" ]; then
    cp -a "$target" "$backup"
  fi
}

backup_file() {
  local target="$1"
  local backup="${target}.bak"
  if [ -f "$target" ] && [ ! -f "$backup" ]; then
    cp -a "$target" "$backup"
  fi
}

ensure_base_packages() {
  pacman -S --needed --noconfirm \
    git \
    base-devel \
    curl \
    wget \
    unzip \
    tar \
    xz \
    fontconfig \
    jq \
    fzf
}

ensure_yay() {
  if runuser -u "$TARGET_USER" -- bash -lc "command -v yay >/dev/null 2>&1"; then
    return
  fi
  ensure_base_packages
  tmpdir="$(mktemp -d)"
  chown -R "$TARGET_USER":"$TARGET_USER" "$tmpdir"
  run_as_user git clone https://aur.archlinux.org/yay.git "$tmpdir/yay"
  run_as_user bash -lc "cd '$tmpdir/yay' && makepkg -s --noconfirm"
  pkgfile="$(ls -1 "$tmpdir"/yay/*.pkg.tar* | head -n 1)"
  pacman -U --noconfirm "$pkgfile"
  rm -rf "$tmpdir"
}

install_packages() {
  ensure_base_packages
  pacman -S --needed --noconfirm \
    neovim \
    zsh \
    podman \
    nodejs \
    npm \
    cuda \
    opencl-nvidia \
    gcc \
    vlc \
    foliate \
    spice-vdagent \
    openvpn \
    openldap \
    nfs-utils \
    docker \
    docker-compose \
    qemu-full \
    virt-manager \
    libvirt \
    ebtables \
    dnsmasq \
    bridge-utils \
    openbsd-netcat \
    bluez \
    bluez-utils \
    virtualbox \
    virtualbox-guest-iso \
    wine \
    wine-gecko \
    john \
    hashcat
  ensure_yay
  local pkgs=(
    hyprland
    waybar
    mako
    hyprpaper
    fuzzel
    ghostty
    zellij
    obsidian
    brave-bin
    vesktop
    spotify
    starship
    navi
    grim
    slurp
    wl-clipboard
    kitty
    greetd
    sysc-greet-hyprland
    qt6ct
    kvantum
    breeze-icons
    adw-gtk3
    ttf-jetbrains-mono-nerd
    flatpak
    go
    pyenv
    python-pipx
  )
  run_as_user yay -S --needed --noconfirm "${pkgs[@]}"
}

set_default_shell() {
  if [ ! -x /bin/zsh ]; then
    echo "zsh not found at /bin/zsh." >&2
    exit 1
  fi
  current_shell="$(getent passwd "$TARGET_USER" | cut -d: -f7)"
  if [ "$current_shell" != "/bin/zsh" ]; then
    chsh -s /bin/zsh "$TARGET_USER"
  fi
}

install_flatpaks() {
  if ! runuser -u "$TARGET_USER" -- bash -lc "command -v flatpak >/dev/null 2>&1"; then
    return
  fi
  if ! run_as_user flatpak --user remote-list | grep -q '^flathub'; then
    run_as_user flatpak --user remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
  fi
  run_as_user flatpak --user install -y flathub com.stremio.Stremio app.zen_browser.zen
}

configure_services() {
  systemctl enable --now docker.service
  usermod -aG docker "$TARGET_USER"

  systemctl enable --now libvirtd
  usermod -aG libvirt "$TARGET_USER"

  systemctl enable --now bluetooth.service

  systemctl enable --now vboxweb.service
  gpasswd -a "$TARGET_USER" vboxusers
  modprobe vboxdrv

  loginctl enable-linger "$TARGET_USER"
  run_as_user systemctl --user enable --now podman.socket
}

install_nerd_font() {
  run_as_user mkdir -p "$TARGET_HOME/.fonts"
  font_zip="$(run_as_user mktemp -p /tmp jetbrainsmono-XXXXXX.zip)"
  run_as_user wget -O "$font_zip" https://github.com/ryanoasis/nerd-fonts/releases/download/v3.3.0/JetBrainsMono.zip
  run_as_user unzip -o "$font_zip" -d "$TARGET_HOME/.fonts"
  run_as_user fc-cache -fv
  rm -f "$font_zip"
}

install_neovim_config() {
  local nvim_dir="$CONFIG_ROOT/nvim"

  if [ -d "$nvim_dir" ]; then
    backup_dir "$nvim_dir"
    rm -rf "$nvim_dir"
  fi

  local nvim_share="$TARGET_HOME/.local/share/nvim"
  if [ -d "$nvim_share" ]; then
    backup_dir "$nvim_share"
    rm -rf "$nvim_share"
  fi

  local nvim_state="$TARGET_HOME/.local/state/nvim"
  if [ -d "$nvim_state" ]; then
    backup_dir "$nvim_state"
    rm -rf "$nvim_state"
  fi

  local nvim_cache="$TARGET_HOME/.cache/nvim"
  if [ -d "$nvim_cache" ]; then
    backup_dir "$nvim_cache"
    rm -rf "$nvim_cache"
  fi

  run_as_user git clone --depth 1 https://github.com/AstroNvim/template "$nvim_dir"
  rm -rf "$nvim_dir/.git"

  if ! grep -q "vim.opt.tabstop = 8" "$nvim_dir/init.lua"; then
    cat >> "$nvim_dir/init.lua" <<'EOF'

vim.opt.tabstop = 8      -- A tab shows as 8 spaces
vim.opt.shiftwidth = 8  -- Indent size
vim.opt.softtabstop = 8 -- Number of spaces a <Tab> counts for
vim.opt.expandtab = true -- Use spaces instead of actual tabs

vim.opt.scrolloff = 10
EOF
  fi

  run_as_user nvim
}

require_paths=(
  "$SCRIPT_DIR/config/hypr/hyprland.conf"
  "$SCRIPT_DIR/config/ghostty/config"
  "$SCRIPT_DIR/config/zellij/config.kdl"
  "$SCRIPT_DIR/config/fuzzel/fuzzel.ini"
  "$SCRIPT_DIR/config/mako/config"
  "$SCRIPT_DIR/config/waybar/config.jsonc"
  "$SCRIPT_DIR/config/waybar/style.css"
  "$SCRIPT_DIR/config/starship/starship.toml"
  "$SCRIPT_DIR/config/zshrc"
  "$SCRIPT_DIR/system/greetd/config.toml"
  "$SCRIPT_DIR/system/greetd/hyprland-greeter-config.conf"
  "$SCRIPT_DIR/system/greetd/kitty.conf"
  "$SCRIPT_DIR/assets/scripts/screenshot.sh"
)

for path in "${require_paths[@]}"; do
  if [ ! -e "$path" ]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
done

install_packages
install_flatpaks
set_default_shell
configure_services
install_nerd_font

backup_dir "$CONFIG_ROOT/hypr"
backup_dir "$CONFIG_ROOT/ghostty"
backup_dir "$CONFIG_ROOT/zellij"
backup_dir "$CONFIG_ROOT/fuzzel"
backup_dir "$CONFIG_ROOT/mako"
backup_dir "$CONFIG_ROOT/waybar"
backup_dir "$CONFIG_ROOT/starship"
backup_file "$TARGET_HOME/.zshrc"
backup_dir "$TARGET_HOME/scripts"
backup_dir "$TARGET_HOME/wallpapers"

sudo mkdir -p /etc/greetd
if [ -d /etc/greetd ] && [ ! -d /etc/greetd.bak ]; then
  sudo cp -a /etc/greetd /etc/greetd.bak
fi

run_as_user mkdir -p "$CONFIG_ROOT/hypr"
run_as_user cp -a "$SCRIPT_DIR/config/hypr/." "$CONFIG_ROOT/hypr/"

run_as_user mkdir -p "$CONFIG_ROOT/ghostty"
run_as_user cp -a "$SCRIPT_DIR/config/ghostty/config" "$CONFIG_ROOT/ghostty/config"

run_as_user mkdir -p "$CONFIG_ROOT/zellij"
run_as_user cp -a "$SCRIPT_DIR/config/zellij/config.kdl" "$CONFIG_ROOT/zellij/config.kdl"

run_as_user mkdir -p "$CONFIG_ROOT/fuzzel"
run_as_user cp -a "$SCRIPT_DIR/config/fuzzel/fuzzel.ini" "$CONFIG_ROOT/fuzzel/fuzzel.ini"

run_as_user mkdir -p "$CONFIG_ROOT/mako"
run_as_user cp -a "$SCRIPT_DIR/config/mako/config" "$CONFIG_ROOT/mako/config"

run_as_user mkdir -p "$CONFIG_ROOT/waybar"
run_as_user cp -a "$SCRIPT_DIR/config/waybar/config.jsonc" "$CONFIG_ROOT/waybar/config.jsonc"
run_as_user cp -a "$SCRIPT_DIR/config/waybar/style.css" "$CONFIG_ROOT/waybar/style.css"

run_as_user mkdir -p "$CONFIG_ROOT/starship"
run_as_user cp -a "$SCRIPT_DIR/config/starship/starship.toml" "$CONFIG_ROOT/starship/starship.toml"

run_as_user cp -a "$SCRIPT_DIR/config/zshrc" "$TARGET_HOME/.zshrc"

run_as_user mkdir -p "$TARGET_HOME/scripts"
run_as_user cp -a "$SCRIPT_DIR/assets/scripts/screenshot.sh" "$TARGET_HOME/scripts/screenshot.sh"
run_as_user chmod +x "$TARGET_HOME/scripts/screenshot.sh"

run_as_user mkdir -p "$TARGET_HOME/wallpapers"
if [ -f "$SCRIPT_DIR/assets/wallpapers/wall.jpg" ]; then
  run_as_user cp -a "$SCRIPT_DIR/assets/wallpapers/wall.jpg" "$TARGET_HOME/wallpapers/wall.jpg"
fi

sudo cp -a "$SCRIPT_DIR/system/greetd/." /etc/greetd/

if [ -f "$SCRIPT_DIR/system/sddm.service.d/override.conf" ]; then
  sudo mkdir -p /etc/systemd/system/sddm.service.d
  sudo cp -a "$SCRIPT_DIR/system/sddm.service.d/override.conf" /etc/systemd/system/sddm.service.d/override.conf
fi

if systemctl list-unit-files | grep -q '^sddm.service'; then
  systemctl disable --now sddm
fi
systemctl enable --now greetd

install_neovim_config

echo "Installation complete. Please reboot and log back in to apply group changes."
