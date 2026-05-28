# Hyprland dotfiles (Arch)

This repo contains a reproducible setup for Hyprland, Ghostty, Zellij, Zsh, Waybar, Mako, Fuzzel, and sysc-greet (greetd).

## Install

Prereq: You should already have **Arch Linux** installed and be able to log in. This script sets up **Hyprland** and related configs; it is not an OS installer.

Run the installer with sudo from the repo root:

```
sudo ./install.sh
```

Notes:
- Uses **yay** for AUR packages.
- Disables **sddm** and enables **greetd**.
- Installs Zen via Flatpak: `app.zen_browser.zen`.
- Installs **Neovim** and replaces `~/.config/nvim` with the AstroNvim template, then launches `nvim`.
