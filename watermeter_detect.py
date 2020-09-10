#!/usr/bin/python3
"""
    Converts image of figures into float value

    Uses the image from watermeter_grab
    Loads watermeter.ini for parameters
    Cuts figure into small parts, each containing 1 number
    Runs each number through the kkn model
        - will save unrecognized numbers into separate directory
        - uses some kind of check to validate number
    Pushes number into database(s)
"""

print("Importing modules...")

# Start logger
import logging
import coloredlogs
logger = logging.getLogger()
# coloredlogs.install(level='CRITICAL')    # Too lazy to change
coloredlogs.install(level='DEBUG')
logging.debug("Logging enabled!")

import configparser
import time
import numpy as np
import cv2
import requests

logger.debug("Done loading modules...")
logger.debug("OpenCV version: {}".format(cv2.__version__))


###[ Acquire image ]##########################################################
def download_image(image_url):
    logger.debug("Downloading image...")

    response = requests.get(image_url)
    image = np.asarray(bytearray(response.content), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)

    return image


###[ CUT CIRCLE ]#############################################################
def cut_circle(image, circle):
    logger.debug("Cutting circle...")

    x, y, r = circle
    roi = image[y-r:y+r, x-r:x+r]
    cv2.imwrite("/var/www/html/watermeter/004_crop.png", roi)

    return roi


###[ ROTATE IMAGE ]###########################################################
def rotate_image(img, angle):
    logger.debug("Rotating image")

    rows, cols = img.shape
    M = cv2.getRotationMatrix2D(
        (cols/2, rows/2),
        180.0*angle / np.pi + 90,
        1)
    dst = cv2.warpAffine(img, M, (cols, rows))

    logger.debug("Writing rotated image")
    cv2.imwrite('/var/www/html/watermeter/007_rotated.png', dst)

    return dst


###[ CUT FIGURES FROM IMAGE ]#################################################
def cut_figures(img, coords, n):
    logger.debug('Cutting the figures from the rotated image...')

    x, y, w, h = coords
    roi = img[y: y+h, x:x+w]
    cv2.imwrite('/var/www/html/watermeter/figures.png', roi)

    logger.debug(f'Amount of numbers: {n}')
    width = round(w/n)

    figures = []
    for i in range(0, n):
        location = width * i
        figure = roi[0: h, location:location+width]
        resized = cv2.resize(figure, (30, 30))
        figures.append(resized)
        cv2.imwrite(
            f'/var/www/html/watermeter/new/{i}-{int(time.time())}.png',
            resized)

    return figures


###[ Analyse figure into number ]#############################################
def analyze_figures(figures):
    """
    #knn = joblib.load('/home/pi/watermeter/knn_model.pkl')
    waterstand = []

    for figure in figures:
        predict = knn.predict(figure.reshape(1, -1))[0]
        predict_proba = knn.predict_proba(figure.reshape(1, -1))
        logger.debug("Best guess: {}, probability: {}".format(
            predict, predict_proba))
        waterstand.append(np.array2string(predict))
        cv2.imwrite(
            "/var/www/html/watermeter/predicted/{}/{}.png".format(predict, time.time()), figure)
    
    return waterstand
    """
    return 0


###[ Push to database ]##############################################################
def push_data(meterstand):
    # Pushes gauge to domoticz

    payload = {'type': 'command',
               'param': 'udevice',
               'idx': '36',
               'svalue': meterstand,
               }
    r = requests.get('http://192.168.178.11:8080/json.htm', params=payload)


###[ MAIN LOOP ]##############################################################
def detect():
    logger.debug("Starting main loop")

    logger.debug('Loading config file')
    config = configparser.ConfigParser()
    parser = config.read('/home/pi/watermeter/watermeter.ini')

    logger.debug('Check if config file is read')
    if not parser:
        logger.error('Config file not loaded, aborting...')
        quit(-1)

    # Download image from server
    full_image = download_image(config['watermeter']['image_url'])

    # Cut into gauge
    circle = cut_circle(
        full_image,
        [int(i) for i in config['watermeter']['coordinates'].split(',')])

    # Rotate gauge
    rotated = rotate_image(
        circle,
        float(config['watermeter']['angle']))

    # Cut into figures only
    figures = cut_figures(
        rotated,
        [int(i) for i in config['watermeter']['figures'].split(',')],
        int(config['watermeter']['amount']))

    # Convert picture into actual numbers
    numbers = analyze_figures(
        figures,
        )

    # Divide by 100, the last two numbers are behind the digit
    meterstand = float(numbers)/100.0

    logger.info("Meterstand: {}".format(meterstand))
    
    logger.debug("Main loop finished")


if __name__ == '__main__':
    detect()
