import board

sqwPin = board.MOSI
dstPin = board.MISO

time24h = True

# ~~~~~ End of configuration! ~~~~~

import asyncio
import countio
import busio as io
import time
import digitalio
import analogio
import math

ldr = analogio.AnalogIn(board.A1)

i2c = io.I2C(board.SCL, board.SDA)

dstSelect = digitalio.DigitalInOut(dstPin)
dstSelect.pull = digitalio.Pull.DOWN # Active is high, uses the internal pull down
dst = dstSelect.value   # Reads the DST switch position and puts it in DST

# Sets the SQW pin to output a 1Hz square wave
while not i2c.try_lock():
    pass
i2c.writeto(0x68, bytes([0x0E,0x00]))   # Disables interupt control and enables squarewave output
i2c.unlock()    # We're done, so unlocks I2C bus

# Imports DS3231
import adafruit_ds3231
rtc = adafruit_ds3231.DS3231(i2c)

if False:  # change to True if you want to set the time
    #                     year, mon, date, hour, min, sec, wday, yday, isdst
    rtc.datetime = time.struct_time((2022, 7, 6, 11, 7, 0, 3, -1, -1))
    # you must set year, mon, date, hour, min, sec and weekday
    # yearday is not supported, isdst can be set but we don't do anything with it at this time

# Imports 7 segment display and backpack
import adafruit_ht16k33.segments
display = adafruit_ht16k33.segments.Seg7x4(i2c)

display.auto_write = False  # Disable auto-write; use .show() to write to the screen
display.brightness = 1 # Sets the brightness to full

t = rtc.datetime    # Gets current datetime
display.print("{:02}{:02}".format(t.tm_hour, t.tm_min))    # Prints current datetime to the screen (each number has to be 2 digits long, so adds a leading 0)
display.show()  # Writes to the screen

cursor = [";",":"]  # ; is middle lights off, : is on

### ~~~~~Functions go here!~~~~~

def screenBrightness():
    measures = []
    for _ in range(100):
        measures.append(ldr.value/65535)
        time.sleep(0.01)
    
    # Rounds up to 2 decimal places
    result = math.ceil((sum(measures)/len(measures))*100)/100
    
    result = result + 0.3   # Adds some brightness to account for the covered front; comment out if you don't need it

    result = max(min(result, 1), 0) # Makes sure the result stays between 1 and 0

    # Then returns the result
    #print (result)
    return (result)

async def catch_interrupt(pin):
    with countio.Counter(pin) as interrupt:
        b = False
        while True:
            if interrupt.count > 0:
                interrupt.count = 0
                b = not b
                t = rtc.datetime
                
                display.print("{}{:02}".format(t.tm_hour, t.tm_min))
                display.print(cursor[b])
                # print("The time is {}:{:02}:{:02}".format(t.tm_hour+dst, t.tm_min, t.tm_sec))

                display.show()
            
            display.brightness = screenBrightness();
            await asyncio.sleep(0)

async def main():
    interrupt_task = asyncio.create_task(catch_interrupt(sqwPin))
    await asyncio.gather(interrupt_task)

asyncio.run(main())