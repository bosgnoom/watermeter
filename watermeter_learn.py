#!/usr/bin/python3
"""

https://towardsdatascience.com/scanned-digits-recognition-using-k-nearest-neighbor-k-nn-d1a1528f0dea
https://www.datacamp.com/community/tutorials/k-nearest-neighbor-classification-scikit-learn


Afmetingen getallen:
    0: 28 en 31 bij 34 pixels
    1: 32 x 34 
    2: 31,32 x 34
    3: 33, 32 en 31 x 34 pix

    ==> resize alles naar 30x30 pixels 
"""

# Start logger
import logging
import coloredlogs
logger = logging.getLogger()
# coloredlogs.install(level='CRITICAL')    # Too lazy to change each time
coloredlogs.install(level='DEBUG')
logger.debug('Importing libraries...')


# Import remaining libraries
import numpy as np
import os

# Show openCV version
import cv2
logger.debug("OpenCV version: {}".format(cv2.__version__))


features_list = []
features_label = []
# Import labeled training data
# Loop over the 10 directories where each directory stores the images of a digit
for digit in range(0, 10):
    print("Reading number: {}".format(digit))
    label = digit
    training_directory = 'learn/' + str(label) + '/'
    for filename in os.listdir(training_directory):
        if (filename.endswith('.png')):
            # Read image and convert into 30x30 image
            training_digit_image = cv2.imread(training_directory + filename, 0)
            training_digit_image = cv2.resize(training_digit_image, (30,30))

            # Convert the image into a 1D array
            training_digit = training_digit_image.ravel()

            # Append to training set
            features_list.append(training_digit)
            features_label.append(label)

# Initiate knn
knn = cv2.ml.KNearest_create()
knn.train(features_list, cv2.ml.ROW_SAMPLE, features_label)
