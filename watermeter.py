#!/usr/bin/python3

"""
    Original work. Will be edited in future
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

from sklearn.neighbors import KNeighborsClassifier
from sklearn.externals import joblib


# Start logger
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
        with picamera.PiCamera() as camera:
            logger.info("Setting camera settings, delay")
            # v2: 3280x2464  3296x2464
            camera.resolution = (3280, 2464)
            camera.exposure_mode = "verylong"

            camera.start_preview()

            time.sleep(5)

            logger.info("... delay done, Capturing image")
            image = np.empty((2464, 3296, 3), dtype=np.uint8)
            camera.capture(image, 'bgr')

    except:
        logger.critical("Camera not available")
        quit(-1)

    #logger.info("Writing full image")
    #cv2.imwrite("/var/www/html/watermeter/001_full.png", image)

    logger.debug("Convert to gray")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("/var/www/html/watermeter/002_gray.png", gray)
    
    return gray


###[ Find circles ]################################
def find_circle(image):
    logger.info("Looking for circles")

    logger.debug("Blur image")
    img = cv2.medianBlur(image, 5)
    
    logger.debug("Running HoughCircles")
    circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1, 20, 
        param1=75, param2=200, minRadius=100, maxRadius=300)

    logger.debug("Circles: {}".format(circles))

    # Capture this in a try... except, as sometimes no circles are detected. 
    # Quit program with critical error.
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

    return roi  #cimg[y-r:y+r, x-r:x+r]


###[ Rotate image ]################################
def rotate_image(img):
    logger.info("Rotating image")
    
    logger.debug("Convert to color")
    cimg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    
    logger.debug("Blurring image")
    img_gray = cv2.medianBlur(img, 5)
    
    logger.debug("Detecting edges")
    edges = cv2.Canny(img_gray, 150, 300)  # Fiddle with these parameters
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

        cv2.line(img, (x1,y1), (x2,y2), (0,0,255), 1)
    
    logger.debug("Writing image with detected lines")
    cv2.imwrite('/var/www/html/watermeter/006_lines.png', img)
    logger.info("Averaged angle: {:0.2f}".format(np.mean(hoek)))
    
    logger.debug("Rotating image")
    rows, cols = img.shape
    M = cv2.getRotationMatrix2D(
        (cols/2, rows/2), 
        180.0*np.mean(hoek)/np.pi + 90,
        1)
    dst = cv2.warpAffine(cimg, M, (cols, rows))
    
    logger.debug("Writing rotated image")
    cv2.imwrite('/var/www/html/watermeter/007_rotated.png', dst)
    
    return dst    #As color image


###[ Find figures ]################################
def find_figures(cimg):
    logger.info("Finding area of figures...")
    result = cimg.copy()

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
    image, contours, hierarchy  = cv2.findContours(
        thresh2, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    cv2.drawContours(cimg, contours, -1, (255,255,0), 1)
    cv2.imwrite('/var/www/html/watermeter/011_contours.png', cimg)
    
    logger.debug("Drawing contours in image")
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        ratio = w/h
        #logger.debug("coords: {}, ratio: {}".format(
        #    (x,y,w,h), ratio))
        if ratio > 5 and y > 50:     # Filter on area of figures
            cv2.rectangle(cimg, (x,y), (x+w,y+h), (255,0,0),1)
            roi = result[y+2: y+h-2, x+2:x+w-2]
    
    logger.debug("Writing contours image")
    cv2.imwrite('/var/www/html/watermeter/012_contours2.png', cimg)
    cv2.imwrite('/var/www/html/watermeter/013_figures.png', roi)
    
    return roi    # As color image


###[ Find numbers ]################################
def find_numbers(cimg):
    logger.info("Looking for numbers...")
    img = cv2.cvtColor(cimg, cv2.COLOR_BGR2GRAY)
    
    logger.debug("Apply threshold and find contours")
    ret, thresh = cv2.threshold(
        img, 127, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    
    kernel = np.ones((2,2), np.uint8)
    erode = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    image, contours, hierarchy  = cv2.findContours(
        erode, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    cv2.drawContours(cimg, contours, -1, (255,255,0), 1)
    cv2.imwrite('/var/www/html/watermeter/014_numbers.png', image)

    logger.debug("Draw contours on image")
    corners=[]
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        ratio = w/h
        if (h > 17):
            cv2.rectangle(cimg, (x+1,y+1), (x+w-1,y+h-1), (255,0,0),1)
            corners.append([x, y, w, h])
            
    logger.debug("Writing image with contours")
    cv2.imwrite('/var/www/html/watermeter/015_numbers_color.png', cimg)
            
    #Sort the corners from left-to-right
    corners.sort(key = lambda x:x[0])
    
    # Cut out each figure and store in a list
    figures = []
    for corner in corners:
        x,y,w,h = corner
        roi = erode[y: y+h, x:x+w]
        figure = cv2.resize(roi, (30,30))
        figures.append(figure)

    return figures, cimg


###[ Detect numbers ]################################
def analyze_figures(figures):
    knn = joblib.load('/home/pi/watermeter/knn_model.pkl')
    waterstand=[]
 
    for figure in figures:
        predict = knn.predict(figure.reshape(1,-1))[0]
        predict_proba = knn.predict_proba(figure.reshape(1,-1))

        logger.debug("Best guess: {}, probability: {}".format(
            predict, predict_proba))
        if (max(predict_proba[0]) < 0.9):
            cv2.imwrite("/var/www/html/watermeter/predicted/{}/{}.png".format(
                predict, time.time()), figure)
 
        waterstand.append(np.array2string(predict))
        
    return ''.join(waterstand)
    
   
###[ MAIN LOOP ]################################   
def main():
    logger.debug("Starting main loop")
    configure_leds()
    leds_on()

    full_image = capture_image()

    leds_off()

    circle = find_circle(full_image)
    rotated = rotate_image(circle)
    figures = find_figures(rotated)
    
    waterstand, cimg = find_numbers(figures)
    numbers = analyze_figures(waterstand)

    meterstand = float(numbers)/100.0
    
    cv2.imwrite("/var/www/html/watermeter/predicted/{}-{}.png".format(
        time.time(), meterstand), cimg)
    
    payload = {'type': 'command',
        'param': 'udevice',
        'idx': '36',
        'svalue': meterstand,
        }
    r = requests.get('http://192.168.178.11:8080/json.htm', params=payload)
    #print(r.url)
    #print(r.text)

    logger.debug("Main loop finished")
    

def snel():
    pass
    
    
if __name__ == '__main__':
    main()
    #snel()
    






