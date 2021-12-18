#!/bin/bash
cd "$(dirname "$0")"
sudo sh setup.sh
sleep 5
sudo sh setup.sh
sleep 5
python3 server.py
