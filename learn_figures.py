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

import numpy as np
import os
#import scipy.ndimage
#from skimage.feature import hog
#from skimage import data, color, exposure
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
#from sklearn.externals import joblib
import joblib
#import skimage
#import sklearn
#import imageio
import cv2


features_list = []
features_label = []
# load labeled training / test data
# loop over the 10 directories where each directory stores the images of a digit
for digit in range(0, 10):
    print("Reading number: {}".format(digit))
    label = digit
    training_directory = 'learn/' + str(label) + '/'
    for filename in os.listdir(training_directory):
        if (filename.endswith('.png')):
            training_digit_image = cv2.imread(training_directory + filename, 0)
            training_digit_image = cv2.resize(training_digit_image, (30,30))
            training_digit = training_digit_image.ravel()
            #cv2.imshow('image', training_digit)
            #cv2.waitKey()
            #training_digit = color.rgb2gray(training_digit_image)
            #training_digit = scipy.misc.imresize(training_digit, (30, 30))
            #print(training_digit_image.shape)

            # extra digit's Histogram of Gradients (HOG). Divide the image into 5x5 blocks and where block in 10x10
            # pixels
            #df = hog(training_digit_image, orientations=8, pixels_per_cell=(6, 6), cells_per_block=(1, 1))
            # print(len(df))
       
            features_list.append(training_digit)
            features_label.append(label)

# store features array into a numpy array
#features  = np.array(features_list, 'float64')

# split the labled dataset into training / test sets
X_train, X_test, y_train, y_test = train_test_split(
	features_list, features_label,
	test_size=0.01,
	random_state=42) # train using K-NN

knn = KNeighborsClassifier(n_neighbors=5)

knn.fit(X_train, y_train)# get the model accuracy

model_score = knn.score(X_test, y_test)

print(model_score)
#quit()
# save trained model
joblib.dump(knn, 'knn_model_2.pkl')
