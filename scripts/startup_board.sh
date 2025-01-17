#!/bin/bash

# Switch to superuser
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit
fi

# Define paths
SCRIPTS_DIR="/home/xilinx/primecam_readout/scripts"
ACTIVATE_SCRIPT="$SCRIPTS_DIR/activate"
INIT_SCRIPT="$SCRIPTS_DIR/init.py"

# Ensure the scripts directory exists
if [ ! -d "$SCRIPTS_DIR" ]; then
    echo "Error: Scripts directory does not exist: $SCRIPTS_DIR"
    exit 1
fi

# Ensure the activate script exists
if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    echo "Error: Activate script does not exist: $ACTIVATE_SCRIPT"
    exit 1
fi

# Source the activate script
source "$ACTIVATE_SCRIPT"

# Navigate to the scripts directory
cd "$SCRIPTS_DIR" || { echo "Failed to navigate to $SCRIPTS_DIR"; exit 1; }

# Execute the Python initialization script
python3 "$INIT_SCRIPT"
