#!/usr/bin/python3

'''Copyright (c) 2019, Douglas Otwell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the 'Software'), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import dbus

from advertisement import Advertisement
from service import Application, Service, Characteristic, Descriptor

from datetime import datetime
from time import time


GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
NOTIFY_TIMEOUT = 5000

def encode(string: str) -> 'list[dbus.Byte]':
    encoded = string.encode('utf-8')
    byte_array = [dbus.Byte(b) for b in encoded]
    return byte_array

def decode(byte_array: 'list[dbus.Byte]') -> str:
    encoded = bytearray([int(b) for b in byte_array])
    return encoded.decode('utf-8')


class TextDescriptor(Descriptor):
    DESCRIPTOR_UUID = '2901'

    def __init__(self, characteristic, description):
        self.description = description
        super().__init__(
                self.DESCRIPTOR_UUID,
                ['read'],
                characteristic)

    def ReadValue(self, options):
        return encode(self.description)


class NsAdvertisement(Advertisement):
    def __init__(self, index):
        super().__init__(index, 'peripheral')
        self.add_local_name('ns_server')
        self.include_tx_power = True


class NsService(Service):
    SVC_UUID = '00000000-b1b6-417b-af10-da8b3de984be'

    def __init__(self, index):
        self.volume_update_paused_until = False

        super().__init__(index, self.SVC_UUID, True)
        self.add_characteristic(BrightnessCharacteristic(self))
        self.add_characteristic(VolumeCharacteristic(self))
        self.add_characteristic(PauseVolumeUpdateCharacteristic(self))
    
    def pause_volume_update(self) -> None:
        self.volume_update_paused_until = time() + 5
    
    def resume_volume_update(self) -> None:
        self.volume_update_paused_until = 0
    
    def is_volume_update_paused(self) -> bool:
        return time() < self.volume_update_paused_until


class NsCharacteristic(Characteristic):
    service: NsService
    def __init__(self, uuid, flags, service: NsService):
        super().__init__(uuid, flags, service)


class BrightnessCharacteristic(NsCharacteristic):
    CHARACTERISTIC_UUID = '00000001-b1b6-417b-af10-da8b3de984be'

    def __init__(self, service):
        self.notifying = False

        super().__init__(
                self.CHARACTERISTIC_UUID,
                ['notify', 'read'], service)
        self.add_descriptor(TextDescriptor(self, 'Brightness (unit?)'))

    def get(self) -> str:
        # get brightness
        strtemp = str(datetime.now())
        return encode(strtemp)

    def notify(self) -> bool:
        if self.notifying:
            value = self.get()
            self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])

        return self.notifying

    def StartNotify(self):
        if self.notifying:
            return

        self.notifying = True

        value = self.get()
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])
        self.add_timeout(NOTIFY_TIMEOUT, self.notify)

    def StopNotify(self):
        self.notifying = False

    def ReadValue(self, options):
        value = self.get()

        return value


class VolumeCharacteristic(NsCharacteristic):
    CHARACTERISTIC_UUID = '00000002-b1b6-417b-af10-da8b3de984be'

    def __init__(self, service):
        self.notifying = False
        self.volume_value = self.get_raw()

        super().__init__(
                self.CHARACTERISTIC_UUID,
                ['notify', 'read'], service)
        self.add_descriptor(TextDescriptor(self, 'Volume (unit?)'))

    def get_raw(self) -> str:
        # get volume
        strtemp = str(datetime.now())
        return encode(strtemp)

    def get(self) -> str:
        if self.service.is_volume_update_paused():
            return self.volume_value
        else:
            return self.get_raw()

    def notify(self) -> bool:
        if self.notifying:
            value = self.get()
            self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])

        return self.notifying

    def StartNotify(self):
        if self.notifying:
            return

        self.notifying = True

        value = self.get()
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])
        self.add_timeout(NOTIFY_TIMEOUT, self.notify)

    def StopNotify(self):
        self.notifying = False

    def ReadValue(self, options):
        value = self.get()

        return value


class PauseVolumeUpdateCharacteristic(NsCharacteristic):
    CHARACTERISTIC_UUID = '10000001-b1b6-417b-af10-da8b3de984be'

    def __init__(self, service):
        super().__init__(
                self.CHARACTERISTIC_UUID,
                ['read', 'write'], service)
        self.add_descriptor(TextDescriptor(self,
            'Write 1 to freeze volume output and write 0 to unfreeze. '
            'Will automatically reset after 5 seconds.'))

    def WriteValue(self, value, options):
        value = decode(value)
        print(value)
        if value == '1':
            self.service.pause_volume_update()
        elif value == '0':
            self.service.resume_volume_update()

    def ReadValue(self, options):
        return encode('1' if self.service.is_volume_update_paused() else '0')


app = Application()
app.add_service(NsService(0))
app.register()

adv = NsAdvertisement(0)
adv.register()

try:
    app.run()
except KeyboardInterrupt:
    app.quit()
