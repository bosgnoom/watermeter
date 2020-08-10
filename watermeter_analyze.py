#!/usr/bin/python3

import logging
import coloredlogs

import time
import datetime

import numpy as np
import cv2

import requests

from sklearn.neighbors import KNeighborsClassifier
#from sklearn.externals import joblib
import joblib

# CONSTANTS
IMAGE_URL = 'http://192.168.178.11/watermeter/002_gray.png'
WATERMETER_CIRCLE = [2085, 1216,  250]
CANNY1 = 100
CANNY2 = 150
WATERMETER_ANGLE = 1.68
WATERMETER_COORDS = [145,167,227,34]


# Start logger
logger = logging.getLogger()
coloredlogs.install(level='CRITICAL') #DEBUG')

logger.debug("OpenCV version: {}".format(cv2.__version__))


###[ Acquire image ]##########################################################
def capture_image():
    logger.debug("Downloading image...")
    response = requests.get(IMAGE_URL)
    image = np.asarray(bytearray(response.content), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
    #cv2.imwrite("002_gray.png", image)
 
    return image


###[ Find circles ]################################
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
    cv2.imwrite("003_circles.png", cimage)

    logger.debug("Writing cropped image...")
    circle = circles[0, 0]      # Just take the first circle for cropping
    x = circle[0]
    y = circle[1]
    r = circle[2]
    roi = image[y-r:y+r, x-r:x+r]
    cv2.imwrite("004_crop.png", roi)

    return roi


###[ Find angle and rotate image ]################################
def find_angle(img):
    logger.info("Rotating image")
    
    logger.debug("Convert to color")
    cimg = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    
    logger.debug("Blurring image")
    img_gray = cv2.medianBlur(img, 5)
    
    logger.debug("Detecting edges")
    edges = cv2.Canny(img_gray, CANNY1, CANNY2)  # Fiddle with these parameters
    cv2.imwrite('005_edges.png', edges)
    
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
    cv2.imwrite('006_lines.png', cimg)
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
    cv2.imwrite('007_rotated.png', cdst)
    
    return dst    #As color image


###[ Find figures ]################################
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

    cv2.imwrite('008_meanshift.png', img)
    
    logger.debug("Running threshold...")
    img = cv2.medianBlur(img, 11)
    ret, thresh = cv2.threshold(img, 60, 255, cv2.THRESH_BINARY_INV)
    cv2.imwrite('009_thresh.png', thresh)
    
    logger.debug("Running morphologyEx...")
    kernel = np.ones((20,20), np.uint8)
    thresh2 = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    cv2.imwrite('010_thresh2.png', thresh2)
    
    logger.debug("Finding contours")
    contours, hierarchy  = cv2.findContours(
        thresh2, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    cv2.drawContours(cimg, contours, -1, (255,255,0), 1)
    cv2.imwrite('011_contours.png', cimg)
    
    logger.debug("Drawing contours in image")
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        ratio = w/h
        #logger.debug("coords: {}, ratio: {}".format(
        #    (x,y,w,h), ratio))
        if ratio > 5 and y > 50:     # Filter on area of figures
            cv2.rectangle(cimg, (x,y), (x+w,y+h), (255,0,0),1)
            roi = result[y-2: y+h+2, x:x+w]
            logger.debug('Width and height: {},{}'.format(w, h))
            logger.info('Figure coordinates: [{},{},{},{}]'.format(x, y, w, h))
    
    logger.debug("Writing contours image")
    cv2.imwrite('012_contours2.png', cimg)
    cv2.imwrite('013_figures.png', roi)
    
    return roi    # As color image


###[ Find numbers ]################################
def find_numbers(cimg):
    logger.info("Looking for numbers...")

    if (cimg.ndim == 2):
        # Grayscale image
        img = cimg
    else:
        # Color image
        img = cv2.cvtColor(cimg, cv2.COLOR_BGR2GRAY)
    
    logger.debug("Apply threshold and find contours")
    ret, thresh = cv2.threshold(
        img, 127, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    
    kernel = np.ones((2,2), np.uint8)
    erode = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    contours, hierarchy  = cv2.findContours(
        erode, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    cv2.drawContours(cimg, contours, -1, (255,255,0), 1)
    #cv2.imwrite('014_numbers.png', image)

    logger.debug("Draw contours on image")
    corners=[]
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        ratio = w/h
        if (h > 17):
            cv2.rectangle(cimg, (x+1,y+1), (x+w-1,y+h-1), (255,0,0),1)
            corners.append([x, y, w, h])
            
    logger.debug("Writing image with contours")
    cv2.imwrite('015_numbers_color.png', cimg)
            
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
    knn = joblib.load('/home/pi/watermeter/knn_model_2.pkl')
    waterstand=[]

    for figure in figures:
        predict = knn.predict(figure.reshape(1,-1))[0]
        predict_proba = knn.predict_proba(figure.reshape(1,-1))

        logger.debug("Best guess: {}, probability: {}".format(
            predict, predict_proba))
        if (max(predict_proba[0]) < 0.95):
            cv2.imwrite("/home/pi/watermeter/learn/{}-{}.png".format(
                predict, time.time()), figure)

        waterstand.append(np.array2string(predict))

    return ''.join(waterstand)


###[ CUT CIRCLE ]################################   
def cut_circle(image, circle):
    logger.debug("Cutting circle...")

    x = circle[0]
    y = circle[1]
    r = circle[2]
    roi = image[y-r:y+r, x-r:x+r]
    
    cv2.imwrite("/var/www/html/watermeter/004_crop.png", roi)

    return roi    

###[ ROTATE IMAGE ]###################################
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

###[ CUT FIGURES FROM IMAGE ]####################
def cut_figures(img, coords):
    x,y,w,h = coords
    roi = img[y-2: y+h-2, x:x+w]
    cv2.imwrite('/var/www/html/watermeter/013_figures.png', roi)

    # Manual detection of figures in x-direction:
    # 33, 66, 96, 128, 155, 190, 220
    figures = []
    for i in range(0, 7):
        #print(31*i+3)
        location = 31*i+3
        figure = roi[0: h-2, location:location+31]
        resized = cv2.resize(figure, (30,30))
        figures.append(resized)
        #cv2.imwrite('new/{}_{}.png'.format(int(time.time()), i), resized)

    return figures
    
###[ MAIN LOOP ]################################   
def main():
    logger.debug("Starting main loop")

    full_image = capture_image()
    
    #circle = find_circle(full_image)
    circle = cut_circle(full_image, WATERMETER_CIRCLE)

    #rotated = find_angle(circle)
    rotated = rotate_image(circle, WATERMETER_ANGLE)
    
    #figures = find_figures(rotated)
    figures = cut_figures(rotated, WATERMETER_COORDS)
    
    
    numbers = analyze_figures(figures)

    meterstand = float(numbers)/100.0

    logger.info("Meterstand: {}".format(meterstand))
    """    
    cv2.imwrite("/var/www/html/watermeter/predicted/{}-{}.png".format(
        time.time(), meterstand), cimg)
    """

    payload = {'type': 'command',
        'param': 'udevice',
        'idx': '36',
        'svalue': meterstand,
        }
    r = requests.get('http://192.168.178.11:8080/json.htm', params=payload)

    logger.debug("Main loop finished")
    

if __name__ == '__main__':
    main()
    






