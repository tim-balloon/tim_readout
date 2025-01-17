#!/bin/bash

# Switch to superuser
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root."
    exit
fi

# Navigate to the init script directory
cd /home/xilinx/primecam_readout/scripts/

# Activate the environment
source activate

# Execute the Python initialization script
python3 init.py