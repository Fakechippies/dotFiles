#!/bin/bash

FILE=~/Pictures/screenshot_$(date +%Y%m%d_%H%M%S).png

# Grab area
grim -g "$(slurp)" "$FILE"

# Copy to clipboard
wl-copy < "$FILE"

echo "Saved screenshot to $FILE and copied to clipboard"
