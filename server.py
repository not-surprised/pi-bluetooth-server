#!/usr/bin/python3

from time import time

import dbus

from ble.advertisement import Advertisement
from ble.service import Application, Service, Characteristic, Descriptor

from sensors.brightness_sensor import BrightnessSensor
from sensors.volume_sensor import VolumeSensor


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
volume_sensor = VolumeSensor()
# brightness_sensor.enable_logging = True
# volume_sensor.enable_logging = True


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
        self.brightness = BrightnessCharacteristic(self)
        self.volume = VolumeCharacteristic(self)
        self.pause = PauseVolumeUpdateCharacteristic(self)

        self.add_characteristic(self.brightness)
        self.add_characteristic(self.volume)
        self.add_characteristic(self.pause)

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
        self.previous = 100000000
        self.last_notify = time()

        super().__init__(
                self.CHARACTERISTIC_UUID,
                ['notify', 'read'], service)
        self.add_descriptor(TextDescriptor(self, 'Brightness (lux)'))

    @staticmethod
    def get() -> 'list[dbus.Byte]':
        # get brightness
        try:
            value = brightness_sensor.get()
            str_value = f'{value:.5g}'  # 5 significant figures
            print(f'read brightness: {str_value}')
            return encode(f'{str_value}')
        except Exception as e:
            print('error reading brightness')
            print(e)
            return encode('error')

    def notify(self) -> bool:
        if self.notifying and time() - self.last_notify > 0.2:
            value = self.get()
            num = float(decode(value))
            if abs(self.previous - num > 0.05 + (0.01 * self.previous)):
                self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])
                self.previous = num
                self.last_notify = time()

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
        self.previous = 100000000
        self.last_notify = time()

        super().__init__(
                self.CHARACTERISTIC_UUID,
                ['notify', 'read'], service)
        self.add_descriptor(TextDescriptor(self, 'Volume (unit?)'))

    @staticmethod
    def get_raw() -> 'list[dbus.Byte]':
        # get volume
        try:
            value = volume_sensor.get()
            str_value = f'{value:.5g}'  # 5 significant figures
            print(f'read volume: {str_value}')
            return encode(f'{str_value}')
        except Exception as e:
            print('error reading volume')
            print(e)
            return encode('error')

    def get(self) -> 'list[dbus.Byte]':
        if not self.service.is_volume_update_paused():
            self.volume_value = self.get_raw()
        return self.volume_value

    def notify(self) -> bool:
        if self.notifying and time() - self.last_notify > 0.2:
            value = self.get()
            num = float(decode(value))
            if abs(self.previous - num > 0.5):
                self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])
                self.previous = num
                self.last_notify = time()

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
        text = 'Write 1 to freeze volume output and write 0 to unfreeze. '\
               'Will automatically reset after 5 seconds.'
        self.add_descriptor(TextDescriptor(self, text))

    def WriteValue(self, value, options):
        try:
            value = float(decode(value))
            print('received', value)
            was_paused = self.service.is_volume_update_paused()
            self.service.pause_volume_update()
            if not was_paused:
                self.service.volume.volume_value = value
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

def stop():
    app.quit()
    brightness_sensor.stop()
    volume_sensor.stop()

try:
    app.run()
except KeyboardInterrupt:
    stop()
except:
    stop()
    raise
