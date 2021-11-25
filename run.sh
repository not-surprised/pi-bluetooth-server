#!/bin/bash
cd "$(dirname "$0")"
sudo -E sh setup.sh
/usr/bin/python3 server.py
