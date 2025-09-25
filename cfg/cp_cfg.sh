#!/bin/bash

# Define paths
CFG_DIR="/home/xilinx/tim_readout/cfg"
CFG_BOARD="_cfg_board.bak.py"
CFG_QUEEN="_cfg_queen.bak.py"

cd $CFG_DIR

cp -v $CFG_BOARD _cfg_board.py
cp -v $CFG_QUEEN _cfg_queen.py
