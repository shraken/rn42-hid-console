#!/usr/bin/python
import sys
import time
import serial
import re
import binascii
import struct
import array

"""
	Roving Network RN42 Bluetooth serial interface.  Allows transition
	between 'CMD' and 'DATA' modes.  Useful for setting initial settings
	and transitioning to 'DATA' mode to send raw HID packet bytestream. 

	Author: Nicholas Shrake <shraken@gmail.com>
	Date: 10/7/2015
"""

# FTDI USB-UART bridge to RN42
TTY_USB = "/dev/tty.usbserial-A903FGE6"
BAUDRATE_DEFAULT = 115200
MAX_SCAN_ATTEMPTS = 3

# RN42-HID Length and Descriptor byte map
hid_packet_preamble = {
						'keyboard' : "\x09\x01",
						'mouse' : "\x05\x02",
						'gamepad' : "\x06",
						'joystick' : "\x06"}

# HID raw descriptors (see pg. 8 of RN-HID User Guide)
hid_raw_descriptors = { 'keyboard' : '1',
						'mouse' : '2',
						'consumer' : '3',
						'gamepad' : '6',
						'joystick' : '6'}

# HID Flag Register Bits (see pg. 6 of RN-HID User Guide)
hid_types = { 'keyboard' : '0200',
			  'gamepad' : '0210',
			  'mouse' : '0220',
			  'combo' : '0230',
			  'joystick' : '0240',
			  'digitizer' : '0250',
			  'sensor' : '0260',
			  'usecfg' : '0270'}
try:
	device_port = serial.Serial(
			port=TTY_USB, 
			baudrate=BAUDRATE_DEFAULT)
except Exception, e:
    print "!!! Error opening serial port, failed: " + str(e)
    exit()

mouse_value_format = struct.Struct('B B B B')
keyboard_value_format = struct.Struct('B B')
joystick_value_format = struct.Struct('B B B B B B')

def rn42_scan_expect(output_message, expect_message):
	for i in range(0, MAX_SCAN_ATTEMPTS):
		# clear the out buffer and write our message to the serial
		out = ''
		device_port.write(output_message)

		# wait one second to give RN42 time to buffer input and reply
		time.sleep(1)
		while device_port.inWaiting() > 0:
			out += device_port.read(1)

		if expect_message in out:
			# we found the expected message in the buffer so return true
			return True
	else:
		# if could not find expected message after number of iterations
		# then fail and return boolean false
		return False

def rn42_set_command_mode():
	return rn42_scan_expect("$$$", "CMD")

def rn42_exit_command_mode():
	return rn42_scan_expect("---\r\n", "END")

def rn42_set_hid_mode(requested_mode):
	hid_mode = "SH,%s\r\n" % requested_mode
	return rn42_scan_expect(hid_mode, "AOK")

def rn42_general_action(action_name, action_list, struc_format):
	action_split = action_list.split(",")

	# check if input delimit list matches size of struc we are packing
	if len(action_split) < struc_format.size:
		return False

	# split incoming string of comma delimit into list of ints
	action_split_int = [int(x) for x in action_split]
	# pack into the mouse format
	struc_packed = struc_format.pack(*action_split_int)

	general_values = "\xFD" + hid_packet_preamble[action_name] + struc_packed
	sys.stdout.write('Writing... ')
	print ":".join("{:02x}".format(ord(c)) for c in general_values)
	device_port.write(general_values + '\r\n')

	return True
	
def rn42_mouse_action(action_name, action_text):
	return rn42_general_action(action_name, action_text, mouse_value_format)

def rn42_keyboard_action(action_name, action_text):
	return rn42_general_action(action_name, action_text, keyboard_value_format)

def rn42_joystick_action(action_name, action_text):
	#for i in range(0,100):
	rn42_general_action(action_name, action_text, joystick_value_format)
	#time.sleep(0.1)

# switch/case block
action_func = { 1 : rn42_keyboard_action,
				2 : rn42_mouse_action,
				6 : rn42_joystick_action}

def rn42_bluetooth_console():
	input=1
	while 1:
		input = raw_input(">> ")

		# split for special character
		input_split = input.split("=")

		if input == 'cmdstart':
			# RN42 start command mode for modifying internal parameters
			# like baud rate, HID mode, etc.
			print ">> Attempting to enter CMD mode..."
			print ">> rn42_set_command_mode() = %r" % rn42_set_command_mode()
		elif input == 'cmdexit':
			# RN42 exit command mode and return back to data mode so can
			# send raw packets
			print ">> Attemting to exit CMD mode..."
			print ">> rn42_exit_command_mode() = %r" % rn42_exit_command_mode()
		elif input == 'exit':
			# internal, close the serial port and exit back to console
			print ">> Closing serial port and cleaning up..."
			device_port.close()
			exit()
		elif input_split[0]=='type':
			# special case 1: change the operating HID mode of the device
			if len(input_split)<2:
				sys.stdout.write(">> Incorrect HID type format, type must use type=")
				for key in hid_types:
					sys.stdout.write("%s," % key)
				print ""
			else:
				if input_split[1] in hid_types:
					print ">> Setting RN42-HID type %s (%s)" % \
						(input_split[1], hid_types[input_split[1]])
					print ">> rn42_set_hid_mode = %r" % \
						rn42_set_hid_mode(requested_mode=hid_types[input_split[1]])
				else:
					print ">> Error, no RN42-HID type named %s" % input_split[1]
		elif input_split[0]=='raw':
			# special case 2: raw data stream, just push the data as specified in hex to module
			if len(input_split)<2:
				sys.stdout.write(">> Incorrect HID raw format, type must use raw=")
			else:
				raw_value_bytearray = array.array('B', input_split[1].decode("hex"))
				sys.stdout.write('Writing... ')
				print ":".join("{:02x}".format(c) for c in raw_value_bytearray)
				device_port.write(general_values + '\r\n')
		elif input_split[0]=='action':
			# special case 3: perform a physical action (move mouse, keyboard entry, etc.)
			if len(input_split)<2:
				sys.stdout.write(">> Incorrect HID action format, action must use action=")
				for key in hid_raw_descriptors:
					sys.stdout.write("%s," % key)
				print ""
			else:
				# use 2 regex to extract the action named entry and the comma delimited items
				# match_action_type  = mouse, keyboard, etc.
				# match_action_items = repetitive comma delimited item 
				match_action_type = re.search(r'(.*)\(', input_split[1], re.M|re.I)
				match_action_items = re.search('(?<=\().*(?=\))', input_split[1])

				if match_action_type is None or match_action_items is None:
					print ">> Error, action packet formatted incorrectly"
				else:
					if match_action_type.group(1) in hid_raw_descriptors:
						# python way of doing case/switch and we pass the regex comma
						# delimited as argument
						if action_func[int(hid_raw_descriptors[\
							match_action_type.group(1)])](match_action_type.group(1), \
								match_action_items.group(0)) is False:
							print ">> Error, action syntax was incorrect"
					else:
						print ">> Error, no RN42 action type named %s" % match_action_type.group(1)
		else:
			# otherwise, we are just recieving input on console so push
			# this data to RN42 but append a CRLF and now grab the output
			# text
			device_port.write(input + '\r\n')
			out = ''

			# wait one second to give RN42 time to buffer input and reply
			time.sleep(1)
			while device_port.inWaiting() > 0:
				out += device_port.read(1)

			if out != '':
				print ">>" + out

	# shouldn't get here
	device_port.close();

if __name__=='__main__':
	rn42_bluetooth_console()