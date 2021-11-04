#!/bin/bash

# we need to run this script after every reboot
sh ./setup/set_bluetooth_mac_address.sh
sh ./setup/set_ble_advertising_interval.sh
sh ./setup/reset_bluetooth.sh
