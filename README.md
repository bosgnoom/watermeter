# Watermeter

Purpose: read water metering gauge in my electrical cabinet

A raspberry pi camera is mounted in a BrightPi LED enclosure. The camera is
aimed at my water meter.

Steps to be taken:
* [x] Switch on LEDs (BrightPi) 
* [x] Take picture (~~openCV~~ PiCamera) 
* [x] Analyse picture
    * [x ] Find circle contours (Hough transform) 
    * [x] Find rectangular contour (see credit card OCR) 
    * [x] Rotate to level 
    * [x] Cut out each digit 
* [x] Analyse each digit 
    * [x] Apply kkN nearest neighbour 
* [x] Compile into one number 
* [x] Send number to 
    * [x] Domoticz 
    * [x] InfluxDB 

## Switch on LEDs
The [BrightPi](https://uk.pi-supply.com/products/bright-pi-bright-white-ir-camera-light-raspberry-pi) uses a Semtech SC620 LED driver. It is connected to the Raspberry Pi using I2C.
The (7-bit) I2C address is 0x70. First, set the gain and dimmer control. Switching on/off by writing either 0x00 or 0xFF to the LED control register.

## Using the pi-camera from pyton
- First attempt using OpenCV. It seems it is hard to set the exposure time to "night" or something like this, so
- Second attempt is using python3-picamera, works so far...

# Re-work
The watermeter.py will be split. The first part will take a photo of the watermeter, convert to gray and store it on the local webserver.
The second part will use that image for analysis. In this way, development on my laptop is possible. I still need to find out how to incorporate this into the Python program running on the Raspberry Pi. 

## Virtual environment (venv)
Install venv (Python3) by:
```
python3 -m pip install --user --upgrade pip
python3 -m pip install --user virtualenv
```
Create a virtual environment by:
```
python3 -m venv env
```
Install required pip packages by: ``` pip install -r requirements.txt ```
