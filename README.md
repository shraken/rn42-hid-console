# RN42-HID Interface Script 

A python utility script for interacting with the Microchip/Roving Network RN42-HID device over a serial terminal.  Allows for easy transition between 'CMD' and 'DATA' modes.  Additionally, helper
routines exist to change HID-class enumeration type and also to send raw HID packets following
RN42 packet format.

## Requirements

Get the RN42-HID breakout board here:
https://www.sparkfun.com/products/10938

PySerial:
https://github.com/pyserial/pyserial

## Installation

sudo pip install pyserial

## Using It

* Tested on Mac OSx (10.8.1 & 10.10.5) w/ python 2.7.2/2.7.10

sudo python ./rn42_hid_console.py

## Command Reference

Command       | Second Header
------------- | -------------
cmdstart      | Start command mode
cmdexit       | Exit command mode
type		  | Change the HID descriptor type
action        | Initiate an HID report item and send packet
raw			  | Send a raw packet from hex input
exit          | Exit the console application

## Examples

see gist log:
https://gist.github.com/shraken/59c6384fb438e34b8136