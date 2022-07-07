# SPDX-FileCopyrightText: 2022 Sam Knowles/Sciencegey https://github.com/sciencegey/cirpyClock
# SPDX-License-Identifier: GPL-3

# Simple CircuitPython clock based on a 7 segment display, DS3231 RTC and QT Py RP2040

import board

sqwPin = board.MOSI     # Pin for the square-wave output from the DS3231
dstPin = board.MISO     # Pin for the DST switch

time24h = True  # Whether to display the time in 24 hour format or 12 hour format

# ~~~~~ End of configuration! ~~~~~

import asyncio
import countio
import busio as io
import time
import digitalio
import analogio
import math

ldr = analogio.AnalogIn(board.A0)   # Light sensor for screen brightness

i2c = io.I2C(board.SCL, board.SDA)  # Creates the I2C connection

dstSelect = digitalio.DigitalInOut(dstPin)
dstSelect.pull = digitalio.Pull.DOWN # Active is high, uses the internal pull down
dst = dstSelect.value   # Reads the DST switch position and puts it in DST variable

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
display.brightness = 0 # Sets the brightness to full

cursor = [";",":"]  # ; is middle lights off, : is on

### ~~~~~Functions go here!~~~~~

def screenBrightness():
    # Measures the light-sensor value and averages it
    measures = []
    for _ in range(100):
        measures.append(ldr.value/65535)
        time.sleep(0.01)
    
    # Averages and rounds down to 2 decimal places
    result = math.floor((sum(measures)/len(measures))*100)/100
    
    # result = result + 0.3   # Adds some brightness to account for the covered front; comment out if you don't need it

    result = max(min(result, 1), 0) # Makes sure the result stays between 1 and 0

    # Then returns the result
    #print (result)
    return (result)


async def catch_interrupt(pin):
    with countio.Counter(pin) as interrupt:
        b = False
        while True:
            # If the square wave interupt is triggered, then update the screen
            if interrupt.count > 0:
                interrupt.count = 0
                b = not b   # Toggles the blinky colon
                t = rtc.datetime    # Gets current time from the RTC
                t = time.struct_time([sum(x) for x in zip(t,(0, 0, 0, dst, 0, 0, 0, 0, 0))])    # Adds DST
                
                if time24h:
                    # If it's 24 hour time, just print the current time to the screen
                    display.print("{:02}{:02}".format(t.tm_hour, t.tm_min))
                else:
                    # Otherwise calculate the time in 12 hour format
                    if (t.tm_hour) <= 12:
                        # If it's 12 or below just display the time
                        display.print("{:02}{:02}".format(t.tm_hour, t.tm_min))
                    else:
                        # And if it's after 12, just subtract 12!
                        display.print("{:02}{:02}".format((t.tm_hour)-12, t.tm_min))

                # Makes sure the time doesn't "over-run" if it's DST
                if t.tm_hour == 24 and time24h:
                    display.print("{:02}{:02}".format("00", t.tm_min))
                elif t.tm_hour == 24 and not time24h:
                    display.print("{:02}{:02}".format("12", t.tm_min))
                
                display.print(cursor[b])    # Display the cursor
                # print("The time is {}:{:02}:{:02}".format(t.tm_hour, t.tm_min, t.tm_sec))

                display.show()  # And then write to the display!
            
            display.brightness = screenBrightness();
            await asyncio.sleep(0)

async def main():
    # This just creates the interupt and then runs it
    interrupt_task = asyncio.create_task(catch_interrupt(sqwPin))
    await asyncio.gather(interrupt_task)

asyncio.run(main())