#!/bin/bash

# we need to run this script after every reboot
sh set_bluetooth_mac_address.sh
sh set_ble_advertising_interval.sh
sh reset_bluetooth.sh
