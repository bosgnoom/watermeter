#!/usr/bin/python3
"""
    Uses photo of watermeter,
    download from source,
    tries to detect meter center,
    rotation and
    location of the figures

    Writes information into configfile.ini
"""

import logging
import coloredlogs

import time
import datetime

import numpy as np
import cv2

import requests

import configparser


# Start logger
logger = logging.getLogger()
#coloredlogs.install(level='CRITICAL')
coloredlogs.install(level='DEBUG')

logger.debug("OpenCV version: {}".format(cv2.__version__))


###[ Acquire image ]##########################################################
def download_image(image_url):
    logger.debug("Downloading image...")

    response = requests.get(image_url)
    image = np.asarray(bytearray(response.content), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
 
    return image


###[ Find circles ]###########################################################
def find_circle(image):
    logger.info("Looking for circles")

    logger.debug("Blur image")
    img = cv2.medianBlur(image, 5)
    
    logger.debug("Running HoughCircles")
    circles = cv2.HoughCircles(
        img,
        cv2.HOUGH_GRADIENT,
        1,
        50,
        minRadius=200,
        maxRadius=300)

    logger.debug("Circles: {}".format(circles))

    # Capture this in a try... except, as sometimes no circles are detected. 
    # Quit program with critical error.
    # TODO: convert into ... if circles is not None:
    try:
        circles = np.uint16(np.around(circles))
    except:
        logger.critical("No circles found, aborting...")
        quit(-1)

    logger.debug("Convert to color")
    cimage = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    logger.debug("Drawing circles")
    for i in circles[0,:]:
        # Draw the outer circle
        cv2.circle(cimage, (i[0],i[1]), i[2], (0,255,0), 1)
        # Draw the center of the circle
        cv2.circle(cimage, (i[0],i[1]), 2, (0,0,255), 3)

    logger.debug("Writing image")
    cv2.imwrite("/var/www/html/watermeter/003_circles.png", cimage)

    logger.debug("Writing cropped image...")
    circle = circles[0, 0]      # Just take the first circle for cropping
    x = circle[0]
    y = circle[1]
    r = circle[2]
    roi = image[y-r:y+r, x-r:x+r]
    cv2.imwrite("/var/www/html/watermeter/004_crop.png", roi)

    # Return the coordinates of the circle and the processed image
    return ','.join([str(i) for i in [x, y, r]]), roi


###[ Find angle and rotate image ]############################################
def find_angle(img, CANNY1, CANNY2):
    logger.info("Rotating image")
    
    logger.debug("Convert to color")
    cimg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    
    logger.debug("Blurring image")
    img_gray = cv2.medianBlur(img, 5)
    
    logger.debug("Detecting edges")
    edges = cv2.Canny(img_gray, int(CANNY1), int(CANNY2))  # Fiddle with these parameters
    cv2.imwrite('/var/www/html/watermeter/005_edges.png', edges)
    
    logger.debug("Running HoughLines")
    hoek = []
    lines = cv2.HoughLines(edges, 1, np.pi/180, 100)

    for line in lines:
        rho=line[0][0]
        theta=line[0][1]
        a = np.cos(theta)
        b = np.sin(theta)
        x0 = a*rho
        y0 = b*rho
        x1 = int(x0 + 1000*(-b))
        y1 = int(y0 + 1000*(a))
        x2 = int(x0 - 1000*(-b))
        y2 = int(y0 - 1000*(a))
        
        #if 1 < theta < 2:
        hoek.append(theta)

        cv2.line(cimg, (x1,y1), (x2,y2), (0,0,255), 1)
    
    logger.debug("Writing image with detected lines")
    cv2.imwrite('/var/www/html/watermeter/006_lines.png', cimg)
    logger.info("Averaged angle: {:0.2f}".format(np.mean(hoek)))
    
    logger.debug("Rotating image")
    rows, cols = img.shape
    M = cv2.getRotationMatrix2D(
        (cols/2, rows/2), 
        180.0*np.mean(hoek)/np.pi + 90,
        1)
    dst = cv2.warpAffine(img, M, (cols, rows))
    cdst = cv2.warpAffine(cimg, M, (cols, rows))
    
    logger.debug("Writing rotated image")
    cv2.imwrite('/var/www/html/watermeter/007_rotated.png', cdst)
    
    return str(np.mean(hoek)), dst    # As color image


###[ Find figures ]###########################################################
def find_figures(cimg):
    logger.info("Finding area of figures...")
    result = cimg.copy()

    logger.debug("Amount of dimensions in image: {}".format(cimg.ndim))

    if (cimg.ndim == 2):
        # Grayscale image
        img = cimg
    else:
        # Color image
        img = cv2.cvtColor(cimg, cv2.COLOR_BGR2GRAY)

    cv2.imwrite('/var/www/html/watermeter/008_meanshift.png', img)
    
    logger.debug("Running threshold...")
    img = cv2.medianBlur(img, 11)
    ret, thresh = cv2.threshold(img, 60, 255, cv2.THRESH_BINARY_INV)
    cv2.imwrite('/var/www/html/watermeter/009_thresh.png', thresh)
    
    logger.debug("Running morphologyEx...")
    kernel = np.ones((20,20), np.uint8)
    thresh2 = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite('/var/www/html/watermeter/010_thresh2.png', thresh2)
    
    logger.debug("Finding contours")
    contours, hierarchy  = cv2.findContours(
        thresh2, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    cv2.drawContours(cimg, contours, -1, (255,255,0), 1)
    cv2.imwrite('/var/www/html/watermeter/011_contours.png', cimg)
    
    logger.debug("Drawing contours in image")
    coords = []

    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        ratio = w/h

        if ratio > 5 and y > 50:     # Filter on area of figures
            cv2.rectangle(cimg, (x,y), (x+w,y+h), (255,0,0),1)
            roi = result[y-2: y+h+2, x:x+w]
            logger.debug('Width and height: {},{}'.format(w, h))
            logger.info('Figure coordinates: [{},{},{},{}]'.format(x, y, w, h))
            coords = ','.join([str(i) for i in [x, y, w, h]])
    
    logger.debug("Writing contours image")
    cv2.imwrite('/var/www/html/watermeter/012_contours2.png', cimg)
    cv2.imwrite('/var/www/html/watermeter/figures.png', roi)
    
    return coords, roi    # As color image


###[ MAIN LOOP ]##############################################################   
def main():
    logger.debug("Starting main loop")
    # Loads config parameters from ini file
    # Configparser is referred to directly. No idea whether this is good programming...

    logger.debug("Loading config file...")
    config = configparser.ConfigParser()
    parser = config.read('watermeter.ini')

    if not parser:
        logger.error('Config file not found, using defaults...')
        config['watermeter'] = {}
        config['watermeter']['image_url'] = 'http://192.168.178.11/watermeter/watermeter.png'
        config['watermeter']['CANNY1'] = '100'
        config['watermeter']['CANNY2'] = '150'

    logger.debug(f'Parser: {parser}')

    # First, get image, to be processed
    logger.debug('Downloading full image...')
    full_image = download_image(config['watermeter']['image_url'])
    
    # Second, look for circles (gauge)
    logger.debug('Looking for circles...')
    config['watermeter']['coordinates'], circle = find_circle(full_image)

    # Rotate figures into view
    config['watermeter']['angle'], rotated = find_angle(
        circle, 
        config['watermeter']['CANNY1'],
        config['watermeter']['CANNY2'])
    
    # Find and cut figures from gauge
    config['watermeter']['figures'], figures = find_figures(rotated)

    # Save config file
    logger.debug('Writing config file...')
    with open('watermeter.ini', 'w') as configfile:
        config.write(configfile)
    
    logger.debug("Main loop finished")
    

if __name__ == '__main__':
    main()
    