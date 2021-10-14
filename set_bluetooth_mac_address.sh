#!/bin/bash

# randomize the mac address
bdaddr -i hci0 B8:27:EB$(hexdump -n3 -e '/1 ":%02X"' /dev/random)

# bdaddr -i hci0 B8:27:EB:24:A3:A8
