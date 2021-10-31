#!/usr/bin/python3
"""
    Takes a photo of my watermeter,
    cuts, rotates and analyses the image,
    pushes value to domoticz
"""

import smbus
import time
import logging
import picamera
import numpy as np
import cv2
import configparser
import argparse
import requests
import os


###[ Start logger ]#############################################################
# Logging, normal logging is CRITICAL
LOGLEVEL = logging.INFO
logging.basicConfig(level=LOGLEVEL)


###[ LED control ]##############################################################
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
    logging.debug("Switching LEDs on")
    i2c_bus.write_byte_data(0x70, 0x00, 0xFF)


def leds_off():
    i2c_bus = smbus.SMBus(1)

    #Switchs all LEDs off
    logging.debug("Switching LEDs off")
    i2c_bus.write_byte_data(0x70, 0x00, 0x00)


###[ Acquire image ]############################################################
def capture_image():
    try:
        logging.debug("Setting camera settings")

        with picamera.PiCamera() as camera:
            # v2: 3280x2464  3296x2464

            # Here I tried to set the camera to "night mode" or something like that,
            # but this caused the PiCamera to freeze...
            # With the default settings the photo is of good enough qulity, keep
            # it like it is for now...
            camera.resolution = (3280, 2464)

            for i in range(20, 0, -1):
                logging.debug("Going to sleep for {} sec...".format(i))
                time.sleep(1)

            camera.exposure_mode = "off"

            logging.debug("... delay done, Capturing image")
            logging.debug("Allocate empty numpy array")
            image = np.empty((2464, 3296, 3), dtype=np.uint8)
            logging.debug("Grabbing image")
            camera.capture(image, 'bgr')
            logging.debug("Image grabbed")
            camera.framerate=5

    except:
        logging.critical("Camera not available")
        leds_off()
        quit(-1)

    finally:
        logging.debug("Camera closed")

    logging.debug("Convert to gray")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("/var/www/html/watermeter.png", image)

    return gray 


###[ Grab image from camera ]##################################################
def grab_image():
    logging.debug("Grab image from camera")

    configure_leds()
    leds_on()
    full_image = capture_image()
    leds_off()

    return full_image


###[ Cut numbers from image ]###################################################
def get_watermeter_numbers(img):
    # Process image:
    # - Cut ROI
    # - Rotate to level
    # - Save each figure as separate file

    logging.debug('Loading config.ini')
    config = configparser.ConfigParser()
    config.read('/home/pi/watermeter/watermeter.ini')

    # Get ROI coordinates
    roi_x1 = int(config['watermeter']['roi_x1'])
    roi_y1 = int(config['watermeter']['roi_y1'])
    roi_x2 = int(config['watermeter']['roi_x2'])
    roi_y2 = int(config['watermeter']['roi_y2'])

    logging.debug('Cut out ROI and convert to binary image')
    roi = img[roi_y1:roi_y2, roi_x1:roi_x2]
    otsu_ret, otsu_img = cv2.threshold(
        roi,
        0, 255,
        cv2.THRESH_BINARY+cv2.THRESH_OTSU)

    #logging.debug('Writing ROI')
    cv2.imwrite("/var/www/html/roi.png", roi)
    cv2.imwrite('/var/www/html/otsu.png', otsu_img)

    logging.debug('Rotating image')
    angle = float(config['watermeter']['angle'])

    rows, cols = otsu_img.shape
    M = cv2.getRotationMatrix2D(
        (cols/2, rows/2),
        angle+180,
        1)
    otsu_rot = cv2.warpAffine(otsu_img, M, (cols, rows))
    
    # Convert otsu image back into BGR to draw the roi of the numbers
    otsu_color = cv2.cvtColor(otsu_rot, cv2.COLOR_GRAY2BGR)

    logging.debug('Writing separated figures to file')
    for i, item in enumerate(config.items('cijfers')):
        # loop over each item in the 'cijfers' part of the ini file
        figure, roi = item
        
        region = [int(j) for j in roi.split(',')]
        
        roi = otsu_rot[region[1]:region[3], region[0]:region[2]]
        cv2.rectangle(
            otsu_color, 
            (region[0],region[1]), 
            (region[2],region[3]), 
            (0,0,255), 
            1)
        
        fig = cv2.resize(roi, (25, 25))

        cv2.imwrite('/var/www/html/{}.png'.format(i), fig)
    
    logging.debug("Writing rotated image")
    cv2.imwrite('/var/www/html/rotated-roi.png', otsu_color)


###[ Analyse figures to number ]################################################
def analyse_figures():
    # Read numbers,
    # process through template matching
    # calculate watermeter value
    
    # Start with 0000000
    prediction = [0] * 7
    
    # Keep track of the maximum score
    max_score = [0] * 7
    
    # Load figures to be analyzed, minimize disk load
    figures = []
    for i in range(7):
        logging.debug('Reading figure {}'.format(i))
        figure = cv2.imread('/var/www/html/{}.png'.format(i), 0)
        figures.append(figure)    
       
    # Loop over template folders [j], (template)match to figures [i]
    for j in range(10):
        logging.debug('Matching templates for {}'.format(j))
        
        # Get files in template folder
        for filename in os.listdir('/home/pi/watermeter/{}/'.format(j)):
            # Only process png files
            if (filename.endswith('.png')):
                # Load template image
                template = cv2.imread(
                    '/home/pi/watermeter/{}/{}'.format(j, filename), 0)
                
                # Match template against each pre-loaded figure
                for i in range(7):
                    res = cv2.matchTemplate(
                        figures[i], 
                        template, 
                        cv2.TM_CCOEFF_NORMED)
                    # Normalize res to score (plain float value)
                    score = res[0][0]
                    
                    # If score's better than before, store it and
                    # update figure
                    if score > max_score[i]:
                        max_score[i] = score
                        prediction[i] = j

    logging.debug('Prediction : {}'.format(prediction))
    logging.debug('Scores: {}'.format(max_score))

    # Calculate accuracy score
    accuracy = calculate_accuracy(max_score)

    # Convert list into number,
    # Also check for bad matched numbers
    meterstand = 0.0
    for i in range(7):
        meterstand = meterstand + prediction[i] * 10 ** (4-i)
        if max_score[i] < 0.8:
            # No good figure found, save it for analysis
            logging.warning('Bad matched figure found, saving for analysis...')
            cv2.imwrite(
                '/home/pi/watermeter/learn/{}-{}.png'.format(
                    int(time.time()), i), 
                    figures[i])
    
    logging.info('Meterstand: {:7.2f}'.format(meterstand))
    logging.info('Combined score: {}'.format(accuracy))
    
    # Catch unreliable reading
    if min(max_score) < 0.6:
        logging.error('Prediction accuracy too low, skipping measurement')
        return 0
    
    return meterstand


###[ Calculate accuracy ]########################################################   
def calculate_accuracy(scores):
    # Calculate accuracy as one number between 0 and 1:
    # Something like a r²: as the product of each score squared
    result = 1
    for i in scores:
        result = result * i**2
    
    return result


###[ Validate  reading ]########################################################   
def validate(meterstand, forced):
    # Check that the reading is correct
    # The last reading is stored in the config file,
    # only accept if:
    #   - reading is equal
    #   - reading is less than 5 m3 more
    config = configparser.ConfigParser()
    config.read('/home/pi/watermeter/watermeter.ini')
    
    last_measurement = config['meterstand'].getfloat('laatste')
    
    logging.debug('Last measurement from configfile: {}'.format(
        last_measurement))
    
    if ((meterstand >= last_measurement) and 
       ((meterstand - last_measurement) < 0.5)) or forced:
        # Value is accepted
        if forced:
            logging.debug('Measurement will be accepted anyway')
        else:
            logging.debug('Measurement is accepted')
       
        # Write into config file
        with open('/home/pi/watermeter/watermeter.ini', 'w') as configfile:
            config['meterstand']['laatste'] = '{:7.2f}'.format(meterstand)
            config.write(configfile)
        
        # Return new and validated value
        return meterstand
    else:
        # Measurement deviates too much from last reading
        logging.error(
            'Measurement value is not OK: {:7.2f}, expected: {:7.2f}'.format(
                meterstand, last_measurement))
        
        # Return last value    
        return last_measurement
        

###[ Domoticz ]#################################################################   
def push_to_domoticz(meterstand):
    # Pushes gauge to domoticz
    logging.debug('Pushing value to domoticz')
    
    payload = {'type': 'command',
               'param': 'udevice',
               'idx': '36',
               'svalue': '{:7.2f}'.format(meterstand),
               }
    r = requests.get('http://192.168.178.11:8080/json.htm', params=payload)

    payload = {'type': 'command',
               'param': 'udevice',
               'idx': '44',
               'svalue': '{}'.format(1000*meterstand),
               }
    r = requests.get('http://192.168.178.11:8080/json.htm', params=payload)


###[ InfluxDB ]#################################################################
def push_to_influx(meterstand):
    # Pushes gauge to influxdb
    logging.debug('Pushing value to influx')
    
    data = 'watermeter watermeter={}\n'.format(meterstand)
    result = requests.post(
        url='http://192.168.178.15:8086/write?db=watermeter', 
        data=data)


###[ Main loop ]################################################################   
if __name__ == '__main__':
    # First, process command line arguments
    parser = argparse.ArgumentParser(
        description='Read water meter gauge by using PiCamera\n'
                    'And processing through template matching'
        )
    parser.add_argument('-q', 
        dest='loglevel_critical', 
        action='store_true',
        default=False,
        help='Run quitly (logging.CRITICAL), default is logging.INFO'
        )
    parser.add_argument('-v', 
        dest='loglevel_debug', 
        action='store_true',
        default=False,
        help='Run verbose (logging.DEBUG), default is logging.INFO'
        )
    parser.add_argument('-f',
        dest='override',
        action='store_true',
        default=False,
        help='Force acceptance of readed meter value'
        )
    parser.add_argument('-m',
        dest='measure',
        action='store_true',
        default=False,
        help='Only process last received image'
        )
    args = parser.parse_args()
    
    if args.loglevel_critical:
        logging.getLogger().setLevel(logging.CRITICAL)
        
    if args.loglevel_debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not(args.measure):
        logging.info("Grabbing picture from camera")
        img = grab_image()
        logging.info("Converting picture")
        get_watermeter_numbers(img)
        
    logging.info("Analyzing picture")
    meterstand = analyse_figures()
    
    meterstand = validate(meterstand, args.override)
    
    logging.info("Pushing value to databases")
    push_to_domoticz(meterstand)
    push_to_influx(meterstand)
        


