# taken from https://forums.adafruit.com/viewtopic.php?f=19&t=175649

from asyncio import sleep
import adafruit_tsl2591

class TSL2591X(adafruit_tsl2591.TSL2591):
    '''
    Description:
    Extend the tsl2591 class with auto-range to realize the full accuracy of the device across it's capable range,
    and also report irradiance in more familiar/useful units.

    Usage:
        import board
        import busio
        import adafruit_tsl2591
        s_tsl2591 = TSL2591X(i2c)
        s_tsl2591.begin()

        # in a loop
        s_tsl2591.autorange()
        # the base class will throw an excpetion if the light is too bright and device becomes saturated
        try:
            print(s_tsl2591.lux)
            # the general rule of thumb is to use 0.0079 * lux for daylight to get W/m^2 so we use that as a sanity check
            print(0.0079 * s_tsl2591.lux, s_tsl2591.irradiance())
        except:
            pass

    Notes:
    channel_0 should probably never be less than channel_1 under normal circumstances so we set the gain and integration
    time based only on channel_0.

    There are 24 combinations of gain and integration time for this device. Most are not particularly useful for general
    applications so to simplify, we choose 7 that overlap neatly for a bumpless transition between states that also
    enables access to the entire dynamic range of the device.

    Calculate the thresholds for 0.05 and 0.95 of the max range then pick your states.

    Gain Integration(ms)   Max      ATM     Lo     Hi       Rank Thresholds      
       1 100               36863     100       5        95   1    1,843 35,020
       1 200               65535     200      10       190       3,277 62,258
       1 300               65535     300      15       285       3,277 62,258
       1 400               65535     400      20       380       3,277 62,258
       1 500               65535     500      25       475       3,277 62,258
       1 600               65535     600      30       570   2    3,277 62,258
      25 100               36863    2500     125     2,375       1,843 35,020
      25 200               65535    5000     250     4,750   3    3,277 62,258
      25 300               65535    7500     375     7,125       3,277 62,258
      25 400               65535   10000     500     9,500       3,277 62,258
      25 500               65535   12500     625    11,875       3,277 62,258
      25 600               65535   15000     750    14,250       3,277 62,258
     428 100               36863   42800   2,140    40,660   4    1,843 35,020
     428 200               65535   85600   4,280    81,320       3,277 62,258
     428 300               65535  128400   6,420   121,980       3,277 62,258
     428 400               65535  171200   8,560   162,640       3,277 62,258
     428 500               65535  214000  10,700   203,300       3,277 62,258
     428 600               65535  256800  12,840   243,960   5    3,277 62,258
    9876 100               36863  987600  49,380   938,220       1,843 35,020
    9876 200               65535 1975200  98,760 1,876,440   6    3,277 62,258
    9876 300               65535 2962800 148,140 2,814,660       3,277 62,258
    9876 400               65535 3950400 197,520 3,752,880       3,277 62,258
    9876 500               65535 4938000 246,900 4,461,100       3,277 62,258
    9876 600               65535 5925600 296,280 5,629,320   7    3,277 62,258

    Reference:
    https://www.adafruit.com/product/1980       
    https://github.com/adafruit/Adafruit_CircuitPython_TSL2591
    https://cdn-learn.adafruit.com/assets/assets/000/078/658/original/TSL2591_DS000338_6-00.pdf?1564168468   
    https://github.com/adafruit/Adafruit_CircuitPython_TSL2591
    https://ams.com/documents/20143/36005/AmbientLightSensors_AN000171_2-00.pdf/9d1f1cd6-4b2d-1de7-368f-8b372f3d8517
    '''

    states = (
        {"gain": adafruit_tsl2591.GAIN_LOW,  "integration": adafruit_tsl2591.INTEGRATIONTIME_100MS, "lo":1843, "hi":35020},
        {"gain": adafruit_tsl2591.GAIN_LOW,  "integration": adafruit_tsl2591.INTEGRATIONTIME_600MS, "lo":3277, "hi":62258},
        {"gain": adafruit_tsl2591.GAIN_MED,  "integration": adafruit_tsl2591.INTEGRATIONTIME_200MS, "lo":3277, "hi":62258},
        {"gain": adafruit_tsl2591.GAIN_HIGH, "integration": adafruit_tsl2591.INTEGRATIONTIME_100MS, "lo":1843, "hi":35020},
        {"gain": adafruit_tsl2591.GAIN_HIGH, "integration": adafruit_tsl2591.INTEGRATIONTIME_600MS, "lo":3277, "hi":62258},
        {"gain": adafruit_tsl2591.GAIN_MAX,  "integration": adafruit_tsl2591.INTEGRATIONTIME_200MS, "lo":3277, "hi":62258},
        {"gain": adafruit_tsl2591.GAIN_MAX,  "integration": adafruit_tsl2591.INTEGRATIONTIME_600MS, "lo":3277, "hi":62258},
        )
    state = 2

    # rather than override __init__ in the base class just get the device and the class in sync
    async def begin(self):
        await self.setstate(self.state)

    async def setstate(self, val: int):
        self.gain = self.states[val]['gain']
        self.integration_time = self.states[val]['integration']
        self.state = val
        # disabling and enabling helps to reset the state of the sensor
        self.disable()
        self.enable()
        await sleep(0.1 + 0.1 * (self.integration_time + 1))
 
    async def autorange(self, once: bool):
        while (True):
            channel_0, channel_1 = self.raw_luminosity
            # debug
            # print(self.state, self.states[self.state]['lo'], self.states[self.state]['hi'])
            if channel_0 > self.states[self.state]['hi'] and self.state > 0:
                await self.setstate(self.state - 1)
            elif channel_0 < self.states[self.state]['lo'] and self.state < (len(self.states) - 1):
                await self.setstate(self.state + 1)
            else:
                break
            # debug
            print("auto state %d: %dx @ %dms %d %d" % (self.state, [1, 25, 428, 9876][self.gain >> 4], 100*(self.integration_time + 1), channel_0, channel_1))
            if once:
                break

    '''
    Estimate irradiance in W/m^2

    From the datasheet at GAIN_HIGH and 100MS:
        ch0 264.1 counts/(uW/cm^2)
        ch1  34.9 counts/(uW/cm^2)
    '''
    def irradiance(self):
        channel_0, channel_1 = self.raw_luminosity
        gain_correction = 428 / [1, 25, 428, 9876][self.gain >> 4]
        integration_time_correction = 1 / (self.integration_time + 1)
        f = gain_correction * integration_time_correction
        # we prefer lux instead of W/m^2
        return f * channel_0 / 100.0
        # return (f * channel_0 / 26410.0)
    


    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, tb):
        self.disable()
        print('Turned off brightness sensor')
