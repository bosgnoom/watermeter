#!/usr/bin/python3

import smbus
import time
import logging
import picamera
import numpy as np
import cv2


# Start logger
logging.basicConfig(format='%(levelname)8s: %(message)s', level=logging.DEBUG)

###[ LED control ]############################################################
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


###[ Acquire image ]##########################################################
def capture_image():
    try:
        with picamera.PiCamera() as camera:
            logging.info("Setting camera settings, delay")
            # v2: 3280x2464  3296x2464
            camera.resolution = (3280, 2464)

            camera.start_preview()

            time.sleep(5)

            logging.info("... delay done, Capturing image")
            image = np.empty((2464, 3296, 3), dtype=np.uint8)
            camera.capture(image, 'bgr')

    except:
        logging.error("Camera not available")
        quit(-1)

    logging.info("Writing full image")
    cv2.imwrite("/var/www/html/watermeter/full.png", image)

    logging.debug("Convert to gray")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cv2.imwrite("/var/www/html/watermeter/gray.png", gray)
    
    return gray

###[ Find circles ]################################
def find_circle(image):
    logging.info("Looking for circles")
    logging.debug("Blur image")

    img = cv2.medianBlur(image, 5)
    cimg = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    
    logging.debug("Running HoughCircles")
    circles = cv2.HoughCircles(img, cv2.HOUGH_GRADIENT, 1, 20, 
        param1=75, param2=200, minRadius=100, maxRadius=300)

    circles = np.uint16(np.around(circles))
    
    for i in circles[0,:]:
        # Draw the outer circle
        cv2.circle(cimg, (i[0],i[1]), i[2], (0,255,0), 1)
        # Draw the center of the circle
        cv2.circle(cimg, (i[0],i[1]), 2, (0,0,255), 3)
    
    logging.debug("Writing image")    
    cv2.imwrite("/var/www/html/watermeter/circles.png", cimg)

    logging.debug("Writing cropped image...")
    circle = circles[0, 0]
    x = circle[0]
    y = circle[1]
    r = circle[2]
    roi = cimg[y-r:y+r, x-r:x+r]
    cv2.imwrite("/var/www/html/watermeter/crop.png", roi)
    
    return roi  #cimg[y-r:y+r, x-r:x+r]


def rotate_image(cimg):
    logging.info("Rotating image")
    
    logging.debug("Convert to gray")
    img_gray = cv2.cvtColor(cimg, cv2.COLOR_BGR2GRAY)
    
    logging.debug("Blurring image")
    img = cv2.medianBlur(img_gray, 5)
    
    logging.debug("Detecting edges")
    edges = cv2.Canny(img, 100, 300)
    cv2.imwrite('/var/www/html/watermeter/edges.png', edges)
    
    logging.debug("Running HoughLines")
    hoek = []
    lines = cv2.HoughLines(edges, 1, np.pi/180/10, 150)

    for line in lines:
        #print("Line: {}".format(line[0]))
        #print("rho: {}".format(line[0][0]))
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
        
    cv2.imwrite('/var/www/html/watermeter/lines.png', cimg)    
    logging.info("Averaged angle: {:0.2f}".format(np.mean(hoek)))
    
    rows, cols = img.shape
    M = cv2.getRotationMatrix2D(
        (cols/2, rows/2), 
        180.0*np.mean(hoek)/np.pi + 90,
        1)
    dst = cv2.warpAffine(cimg, M, (cols, rows))
    
    cv2.imwrite('/var/www/html/watermeter/rotated.png', dst)
    
    return dst
    


def main():
    logging.debug("Starting main loop")
    configure_leds()
    leds_on()

    full_image = capture_image()

    leds_off()

    circle = find_circle(full_image)
    rotate_image(circle)

    logging.debug("Main loop finished")
    

if __name__ == '__main__':
    main()
    






