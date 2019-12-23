# Watermeter

Purpose: read water metering gauge in my electrical cabinet

A raspberry pi camera is mounted in a BrightPi LED enclosure. The camera is
aimed at my water meter.

Steps to be taken:
* [x] Switch on LEDs (BrightPi) 
* [x] Take picture (~~openCV~~ PiCamera) 
* [ ] Analyse picture
    * [] Find circle contours (Hough transform) 
    * [] Find rectangular contour (see credit card OCR) 
    * [] Rotate to level 
    * [] Cut out each digit 
* [] Analyse each digit 
    * [] Apply kkN nearest neighbour 
* [] Compile into one number 
* [] Send number to 
    * [] Domoticz 
    * [] InfluxDB 

## Switch on LEDs
The [BrightPi](https://uk.pi-supply.com/products/bright-pi-bright-white-ir-camera-light-raspberry-pi) uses a Semtech SC620 LED driver. It is connected to the Raspberry Pi using I2C.
The (7-bit) I2C address is 0x70. First, set the gain and dimmer control. Switching on/off by writing either 0x00 or 0xFF to the LED control register.

## Using the pi-camera from pyton
- First attempt using OpenCV. It seems it is hard to set the exposure time to "night" or something like this, so
- Second attempt is using python3-picamera

