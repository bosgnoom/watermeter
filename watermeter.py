#!/usr/bin/python3

import smbus
import time
import cv2
import logging


# Start logger
logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)

###[ LED control
def configure_leds():
    i2c_bus = smbus.SMBus(1)

    # Set the dimming control for all leds to 40, 
    # 40x.28125=11.25 mA for each LED
    logging.debug("Set LED dimming control")
    for i in range(1, 8):
        i2c_bus.write_byte_data(0x70, i, 40)

    # Set the gain control to 0x08h (default, 281.25 micro-ampere)
    logging.debug("Set LED gain control")
    i2c_bus.write_byte_data(0x70, 0x09, 0x08)


def leds_on():
    i2c_bus = smbus.SMBus(1)

    #Switch all (outer) LEDs on
    logging.info("Switching LEDs on")
    i2c_bus.write_byte_data(0x70, 0x00, 0xFF)


def leds_off():
    i2c_bus = smbus.SMBus(1)

    #Switchs all LEDs off
    logging.info("Switching LEDs off")
    i2c_bus.write_byte_data(0x70, 0x00, 0x00)


###[ Image processing
def capture_image():
    logging.info("Capturing image")
    cap = cv2.VideoCapture(0)

    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            logging.debug("Frame was read")


def main():
    logging.debug("Starting main loop")
    configure_leds()
    leds_on()

    capture_image()

    leds_off()
    
    logging.debug("Main loop finished")
    

if __name__ == '__main__':
    main()
    






