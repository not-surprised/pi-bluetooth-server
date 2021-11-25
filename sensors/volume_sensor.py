import math

import sounddevice as sd
import numpy as np


class CircularBuffer(np.ndarray):
    def __new__(cls, max_length: int):
        return np.zeros(max_length).view(cls)

    def __init__(self, max_length: int):
        self._length = 0
        self._max_length = max_length
        self._index = 0
        
    def push(self, value: float):
        if self._length < self._max_length:
            self._length += 1

        self[self._index] = value
        self._index += 1
        self._index %= len(self)
    
    def populated_slice(self) -> np.ndarray:
        if self._length < self._max_length:
            return self[:self._length]
        else:
            return self


class VolumeSensor:

    def __init__(self):
        self.buffer = CircularBuffer(100)
        self.enable_logging = False
        self.value: float = 0
        self.start()
    
    def get(self):
        return self.value
    
    def start(self):
        self.stream = sd.InputStream(samplerate=48000, latency=0.2, channels=1, callback=self.callback)
        self.stream.start()
    
    def stop(self):
        self.stream.stop()
        self.stream.close()
        print('Turned off microphone stream')

    def callback(self, indata: np.ndarray, frames, time, status):
        sample = self.toDecibels(indata)
        self.buffer.push(sample)
        self.value = self.time_average(self.buffer.populated_slice(), 0.8)
        if self.enable_logging:
            self.print_sound(self.value)

    @classmethod
    def rms(cls, arr: np.ndarray) -> float: # calculates root mean squared of an array of sound data
        rms = np.sqrt(np.mean(arr ** 2))
        return rms

    @classmethod
    def toDecibels(cls, pressure: np.ndarray) -> float:
        p = cls.rms(pressure)
        pp0 = abs(p / 0.00002) # rms / threshold
        if (pp0 > 0.00000001): # ensures the value is not too close to 0 (or is 0)
            decibels = 20 * math.log(pp0 , 10) # converstion to decibels
        else:
            decibels = 0
        return decibels

    @classmethod
    def time_average(cls, samples: np.ndarray, percentage: float) -> float:
        index = int(percentage * len(samples))
        index = max(0, index)
        index = min(len(samples) - 1, index)
        return np.partition(samples.flatten(), index)[index]

    @classmethod
    def print_sound(cls, level: float):
        print('{: >5.1f}'.format(level), '|' * max(0, int(level)))


if __name__ == '__main__':
    sensor = VolumeSensor()
    sensor.enable_logging = True
    try:
        while sensor.stream.active:
            sd.sleep(100)
    except KeyboardInterrupt:
        sensor.stop()
