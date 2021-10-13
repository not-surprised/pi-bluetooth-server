#!/bin/bash

INTERVAL_MILLISECONDS=200;
INTERVAL_VALUE=$(($INTERVAL_MILLISECONDS * 8 / 5));

echo $INTERVAL_VALUE > /sys/kernel/debug/bluetooth/hci0/adv_min_interval
echo $INTERVAL_VALUE > /sys/kernel/debug/bluetooth/hci0/adv_max_interval
