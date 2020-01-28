"""

Detect figures

First version, needs a lot of work...

"""

import numpy as np
import os
#import scipy.ndimage
#from skimage.feature import hog
#from skimage import data, color, exposure
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.externals import joblib
#import skimage
#import sklearn
#import imageio
import cv2


knn = joblib.load('knn_model.pkl')


def feature_extraction(image):
    training_digit_image = cv2.imread(image, 0)
    training_digit_image = cv2.resize(training_digit_image, (30,30))
    training_digit = training_digit_image.ravel()

    return training_digit


def predict(df):
    predict = knn.predict(df.reshape(1,-1))[0]
    print(knn.predict(df.reshape(1,-1)))
    predict_proba = knn.predict_proba(df.reshape(1,-1))
    print(predict_proba)
    return predict, predict_proba[0][predict]


# load your image from file
digits = ['4/1570210549-6.png', '6/1570210319-2.png']

features = [ feature_extraction(digit) for digit in digits ]

# extract featuress
#hogs = list(map(lambda x: feature_extraction(x), digits))
#print(hogs)

# apply k-NN model created in previous
predictions = list(map(lambda x: predict(x), features))

print(predictions)



