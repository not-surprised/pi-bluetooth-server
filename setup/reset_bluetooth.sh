#!/bin/bash

hciconfig hci0 reset
systemctl restart bluetooth.service