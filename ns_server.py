#!/usr/bin/python3

from datetime import datetime
from time import time

import dbus

from advertisement import Advertisement
from service import Application, Service, Characteristic, Descriptor

from brightness_sensor import BrightnessSensor


GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
NOTIFY_TIMEOUT = 500

def encode(string: str) -> 'list[dbus.Byte]':
    encoded = string.encode('utf-8')
    byte_array = [dbus.Byte(b) for b in encoded]
    return byte_array

def decode(byte_array: 'list[dbus.Byte]') -> str:
    encoded = bytearray([int(b) for b in byte_array])
    return encoded.decode('utf-8')


brightness_sensor = BrightnessSensor()
# brightness_sensor.enable_logging = True


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
    # we use this to identify that the device is indeed an ns_server
    MANUFACTURER_UNIQUE_IDENTIFIER = '$tZuFTNvsLGt9U^gsCM!t8$@Fd6'

    def __init__(self, index):
        super().__init__(index, 'peripheral')
        self.add_local_name('ns_server')
        self.add_manufacturer_data(0xffff, encode(self.MANUFACTURER_UNIQUE_IDENTIFIER))
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
        self.add_descriptor(TextDescriptor(self, 'Brightness (lux)'))

    def get(self) -> str:
        # get brightness
        try:
            value = brightness_sensor.get()
            str_value = f'{value:.5g}' # 5 significant figures
            print(f'read:{str_value}')
            return encode(f'{str_value}')
        except Exception as e:
            print('error reading sensor')
            print(e)
            return encode('error')

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
        return encode(str(datetime.now()))

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
        try:
            value = decode(value)
            print('received', value)
            if value == '1':
                self.service.pause_volume_update()
            elif value == '0':
                self.service.resume_volume_update()
        except Exception as e:
            print('error in WriteValue')
            print(e)

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
    brightness_sensor.stop_loop()
