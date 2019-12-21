#!/usr/bin/python3

import smbus
import time
import cv2


###[ LED control
def configure_leds():
    i2c_bus = smbus.SMBus(1)

    # Set the dimming control for all leds to 40, 40x.28125=11.25 mA for each LED
    for i in range(1, 8):
        i2c_bus.write_byte_data(0x70, i, 40)

    # Set the gain control to 0x08h (default, 281.25 micro-ampere)
    i2c_bus.write_byte_data(0x70, 0x09, 0x08)


def leds_on():
    i2c_bus = smbus.SMBus(1)

    #Switch all (outer) LEDs on
    print("On")
    i2c_bus.write_byte_data(0x70, 0x00, 0xFF)


def leds_off():
    i2c_bus = smbus.SMBus(1)

    #Switchs all LEDs off
    print("Off")
    i2c_bus.write_byte_data(0x70, 0x00, 0x00)


def capture_image():
    cap = cv2.VideoCapture(0)

    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            print("Frame was read")



configure_leds()
leds_on()

capture_image()

leds_off()






