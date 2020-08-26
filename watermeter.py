#!/usr/bin/python3
"""
    Takes a photo of my watermeter,
    stores as grayscale image on webserver
"""

import smbus
import time
import logging
import chromalog
import picamera
import numpy as np
import cv2
import datetime
import requests


###[] Start logger ]#########################################################
#chromalog.basicConfig(format='%(message)s', level=logging.CRITICAL)
chromalog.basicConfig(format='%(message)s', level=logging.DEBUG)
logger = logging.getLogger()


###[ LED control ]############################################################
def configure_leds():
    i2c_bus = smbus.SMBus(1)

    # Set the dimming control for all leds to 40,
    # 40x.28125=11.25 mA for each LED
    logger.debug("Set LED dimming control")
    for i in range(1, 8):
        i2c_bus.write_byte_data(0x70, i, 40)

    # Set the gain control to 0x08h (default, 281.25 micro-ampere)
    logger.debug("Set LED gain control")
    i2c_bus.write_byte_data(0x70, 0x09, 0x08)


def leds_on():
    i2c_bus = smbus.SMBus(1)

    #Switch all (outer) LEDs on
    logger.info("Switching LEDs on")
    i2c_bus.write_byte_data(0x70, 0x00, 0xFF)


def leds_off():
    i2c_bus = smbus.SMBus(1)

    #Switchs all LEDs off
    logger.info("Switching LEDs off")
    i2c_bus.write_byte_data(0x70, 0x00, 0x00)


###[ Acquire image ]##########################################################
def capture_image():
    try:
        logger.debug("Setting camera settings")

        with picamera.PiCamera() as camera:
            # v2: 3280x2464  3296x2464
            camera.resolution = (3280, 2464)
            camera.sensor_mode=3
            camera.framerate=0.17
            
            camera.exposure_mode = "verylong"

            logger.debug("Going to sleep...")
            time.sleep(20)

            logger.debug("... delay done, Capturing image")
            image = np.empty((2464, 3296, 3), dtype=np.uint8)
            camera.capture(image, 'bgr')

    except:
        logger.critical("Camera not available")
        quit(-1)

    logger.debug("Convert to gray")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("/var/www/html/watermeter/watermeter.png", gray)

    return gray 


###[ MAIN LOOP ]###################################################   
def grab_image():
    logger.debug("Starting main loop")

    configure_leds()
    
    leds_on()

    full_image = capture_image()

    leds_off()

    logger.debug("Main loop finished")
    
if __name__ == '__main__':
    grab_image()




