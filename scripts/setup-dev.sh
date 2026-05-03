#!/bin/bash
# Installs all required OS-level dependencies for PradyOS Development
set -e

echo "Updating package lists..."
sudo apt update

echo "Installing Compositor & UI dependencies..."
sudo apt install -y hyprland rofi waybar

echo "Installing Input Injection & Capture dependencies..."
sudo apt install -y ydotool xdotool grim slurp scrot

echo "Installing AI & Processing dependencies..."
sudo apt install -y tesseract-ocr espeak-ng notify-send nodejs npm python3 python3-pip

echo "Installing HuggingFace CLI..."
pip3 install --break-system-packages huggingface-cli

echo "Environment setup complete."
