import asyncio
import threading

import board
from TSL2591X import TSL2591X


class BrightnessSensor:
    
    def __init__(self):
        self.enable_logging = False
        self.value = 0
        self.keep_running = True
        self.thread = threading.Thread(target=self.start_loop)
        self.thread.start()

    def start_loop(self):
        self.keep_running = True
        asyncio.run(self.loop())

    def stop_loop(self):
        self.keep_running = False

    async def loop(self):
        i2c = board.I2C()
        with TSL2591X(i2c) as sensor:
            await sensor.begin()
            while self.keep_running:
                try:
                    self.value = sensor.irradiance()
                    if self.enable_logging:
                        print(f'brightness:{self.value:.4f}')
                    await asyncio.gather(sensor.autorange(True), asyncio.sleep(0.2))
                except Exception as e:
                    print('Exception in BrightnessSensor.loop:', e)

    def get(self):
        return self.value


if __name__ == '__main__':
    brightness_sensor = BrightnessSensor()
    brightness_sensor.enable_logging = True
