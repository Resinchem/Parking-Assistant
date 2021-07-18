#!/usr/bin/env python

'''
 Parking Assist System using Raspberry Pi 3b+, 32x32 LED panel and 2x TFMini sensors
 October 14, 2019 by Resinchem Tech

 built upon the "runtext.py" example from hzeller/rpi-rgb-led-matrix library.
 Adapted from Instructables project by Dinesh Bhatia
 
 Public Domain 

 Notes:
  run as 'sudo python parking_tf.py'

 Version: 1.3
 Last Update: 10/21/2019
 
 Version: 1.4
   - Added MQTT
 Last Updated: 06/01/2020

 Version: 1.5
   - Added exception handling for MQTT publish
 Last Updated: 07/09/2020

 IMPORTANT:  Update MQTT Publish statement near end of main loop (line 410) 
             with your MQTT Broker information
 Optionally: Change the MQTT Topics in lines 403-407 if you wish to use
             different topics

''' 
from samplebase import SampleBase
from rgbmatrix import graphics
import time
import sys
import serial
import paho.mqtt.publish as publish

#------------------------------------------------------------------------------------------------
# for TFMini sensor control (front sensor)
tfmf = serial.Serial("/dev/ttyUSB0", 115200)
#------------------------------------------------------------------------------------------------

font = graphics.Font()
font.LoadFont("../../../fonts/7x13.bdf")

#------------------------------------------------------------------------------------------------
# You can change these values as needed. 
nom_parked_Front = 200 # Nominal resting position of the car when parked correctly in mm

active_brightness = 75 # Values can be 1 to 100, default 100
sleep_brightness = 1 # Values can be 1 to 100, default 10 

maxOperationTimeParked = 60 # Amount of time in seconds for LED display to be active while parking
maxOperationTimeExit = 5 # Amount of time in seconds for LED display to be active after exiting

printDebugInfo = False  # Useful data for install. You can set this to False to turn it off afterwards, default = False
log_active = True  #Create log file
log_interval = 180  # Create log entry every 180 seconds (3 minutes) - MQTT Publish uses this same interval
#------------------------------------------------------------------------------------------------

_readstatF = "OK"
_exitSleepTimerStarted = False
blink_countMax = 6 # for blinking rate
f_outofrange_countMax = 5
_sensorMaxF = 3000 # max sensor distance in mm for TFMini (this is 118")
_sensorMinF = 30 # min sensor distance in mm (TFMini will report this value for anything less than 30)
_detState = "nocar"  # to keep track of car detection

def stop(self):
    print("Program stopping")
    print("> closing the USB port ")
    flog.close()
    tfmf.close()
    sys.exit()

def clearSideArrows(canvas, red, green, blue):
    len = graphics.DrawText(canvas, font, -1, 20, graphics.Color(red, green, blue), " ")
    len = graphics.DrawText(canvas, font, 26, 20, graphics.Color(red, green, blue), " ")

def DrawP(canvas, red, green, blue):
        _ctrP = [
            0,0,0,0,1,0,0,0,0,
            0,0,0,0,1,0,0,0,0,
            0,0,0,0,1,0,0,0,0,
            0,0,0,0,1,0,0,0,0,
            1,1,1,1,1,1,1,1,1,
            0,0,0,0,1,0,0,0,0,
            0,0,0,0,1,0,0,0,0,
            0,0,0,0,1,0,0,0,0,
            0,0,0,0,1,0,0,0,0,
            ]
           
        for x in range(0,9):
            for y in range(0,9):
                if(_ctrP[x+y*9] == 1):
                    canvas.SetPixel(x+13, y+11,red, green, blue)

def DrawX(canvas, red, green, blue):
        _ctrX = [
            1,0,0,0,0,0,0,0,1,
            0,1,0,0,0,0,0,1,0,
            0,0,1,0,0,0,1,0,0,
            0,0,0,1,0,1,0,0,0,
            0,0,0,0,1,0,0,0,0,
            0,0,0,1,0,1,0,0,0,
            0,0,1,0,0,0,1,0,0,
            0,1,0,0,0,0,0,1,0,
            1,0,0,0,0,0,0,0,1,
            ]
            
        for x in range(0,9):
            for y in range(0,9):
                if(_ctrX[x+y*9] == 1):
                    canvas.SetPixel(x+13, y+11,red, green, blue)


def DrawLeftArrow(canvas, red, green, blue, _blinking):
    if(_blinking):
        len = graphics.DrawText(canvas, font, -1, 20, graphics.Color(red, green, blue), "<")

def DrawRightArrow(canvas, red, green, blue, _blinking):
    if(_blinking):
        len = graphics.DrawText(canvas, font, 26, 20, graphics.Color(red, green, blue), ">")

def DrawUpArrow(canvas, red, green, blue):
        _upArrow = [
            0,0,0,0,1,0,0,0,0,
            0,0,0,1,0,1,0,0,0,
            0,0,1,0,0,0,1,0,0,
            0,1,0,0,0,0,0,1,0,
            1,0,0,0,0,0,0,0,1
            ]

        for x in range(0,9):
            for y in range(0,5):
                if(_upArrow[x+y*9] == 1):
                    canvas.SetPixel(x+13, y+0,red, green, blue)

def DrawDownArrow(canvas, red, green, blue):
        _downArrow = [
            1,0,0,0,0,0,0,0,1,
            0,1,0,0,0,0,0,1,0,
            0,0,1,0,0,0,1,0,0,
            0,0,0,1,0,1,0,0,0,
            0,0,0,0,1,0,0,0,0
            ]
            
        for x in range(0,9):
            for y in range(0,5):
                if(_downArrow[x+y*9] == 1):
                    canvas.SetPixel(x+13, y+27,red, green, blue)

def DrawCorners(canvas, red, green, blue):
        _TRcorner = [
            0,0,0,0,1,1,1,1,1,
            0,0,0,0,0,1,1,1,1,
            0,0,0,0,0,0,1,1,1,
            0,0,0,0,0,0,0,1,1,
            0,0,0,0,0,0,0,0,1
            ]

        _TLcorner = [
            1,1,1,1,1,0,0,0,0,
            1,1,1,1,0,0,0,0,0,
            1,1,1,0,0,0,0,0,0,
            1,1,0,0,0,0,0,0,0,
            1,0,0,0,0,0,0,0,0
            ]

        _BLcorner = [
            1,0,0,0,0,0,0,0,0,
            1,1,0,0,0,0,0,0,0,
            1,1,1,0,0,0,0,0,0,
            1,1,1,1,0,0,0,0,0,
            1,1,1,1,1,0,0,0,0
            ]

        _BRcorner = [
            0,0,0,0,0,0,0,0,1,
            0,0,0,0,0,0,0,1,1,
            0,0,0,0,0,0,1,1,1,
            0,0,0,0,0,1,1,1,1,
            0,0,0,0,1,1,1,1,1
            ]

        for x in range(0,9):
            for y in range(0,5):
                if(_TRcorner[x+y*9] == 1):
                    canvas.SetPixel(x+23, y,red, green, blue)

        for x in range(0,9):
            for y in range(0,5):
                if(_BRcorner[x+y*9] == 1):
                    canvas.SetPixel(x+23, y+27,red, green, blue)

        for x in range(0,9):
            for y in range(0,5):
                if(_BLcorner[x+y*9] == 1):
                    canvas.SetPixel(x, y+27,red, green, blue)

        for x in range(0,9):
            for y in range(0,5):
                if(_TLcorner[x+y*9] == 1):
                    canvas.SetPixel(x, y,red, green, blue)

def Read_Distance_TFMiniF():     #LIDAR Sensor
    if tfmf.is_open == False:
        tfmf.open()
    count = tfmf.in_waiting
    if count > 8:
        recv = tfmf.read(9)
        tfmf.reset_input_buffer()
        if recv[0] == 'Y' and recv[1] == 'Y': # 0x59 is 'Y'
            low = int(recv[2].encode('hex'), 16)
            high = int(recv[3].encode('hex'), 16)
            distance = (low + high * 256) * 10  # multiply by 10 to go from CM to MM
            _readstatF = "OK"
    try:
        return distance
    except:
        _readstatF = "ERR"
        return 2

class RunText(SampleBase):

    def run(self):
        offscreen_canvas = self.matrix.CreateFrameCanvas()

        fontB = graphics.Font()
        fontB.LoadFont("../../../fonts/9x18B.bdf")
      
        blink_count = blink_countMax
        _blinking  = False
        blinkingCorners = False
        _cornerColors = [255,255,255] # white corners initially
		
        Measured_Distance_Front = _sensorMaxF

        _exitSleepTimerStarted = False
        _parkedSleepTimerStarted = False

        _detState = "nocar"
        _powerState = "sleep"
        f_outofrange_count = 0
        displayBrightness = sleep_brightness

        _readstatF = "OK"

        _carDetectCntr = 0
        _carDetectCntrMax = 5
        _carNoDetectCntr = 0
        _carNoDetectCntrMax = 5
        _coldStart = True
        start_time = time.time()  # init value
        # Open log file and record start time
        flog = open("/home/pi/parklog.txt", "w", 0)
        flog.write("Startup: " + time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.localtime()) + "\n")
        logtime_start = time.time() 

#------------------------------------------------------------------------------------------------
# start of main loop
#------------------------------------------------------------------------------------------------
        while True:

            offscreen_canvas.Clear()

            #------------------------------------------------------------------------------------------------
            # Read distances from the TFMini sensor
            #------------------------------------------------------------------------------------------------

            # for the Front sensor
            dF = Read_Distance_TFMiniF()
            if ( dF == 2 ): # status code 4 is phase fail which generally means out of range 
                dF = _sensorMaxF +1
                _readstatF = "ERR"

            if(dF > _sensorMinF):
                Measured_Distance_Front = (dF + Measured_Distance_Front)/2

            if (Measured_Distance_Front < _sensorMinF): # bound the values
                Measured_Distance_Front = _sensorMinF

            if (Measured_Distance_Front > _sensorMaxF): # bound the values
                Measured_Distance_Front = _sensorMaxF                

            self.matrix.brightness = displayBrightness

            if (Measured_Distance_Front < _sensorMaxF):
                if(_detState == "nocar"):
                    _carDetectCntr = _carDetectCntr + 1
                    if (_carDetectCntr > _carDetectCntrMax): # to make sure we don't trigger on noise
                        _carDetectCntr = 0
                        _detState = "car"  # to say we detected the car now 
                        _exitSleepTimerStarted = False
                        _parkedSleepTimerStarted = True
                        start_time = time.time()  # start timer now
                        displayBrightness = active_brightness
                        if(_powerState == "sleep"): 
                            _powerState = "active"
            else:
                _carNoDetectCntr = _carNoDetectCntr + 1
                if (_carNoDetectCntr > _carNoDetectCntrMax): # to make sure we don't trigger on noise

                    if(not _exitSleepTimerStarted):
                        if(_detState == "car" or _coldStart):
                            _exitSleepTimerStarted = True
                            _coldStart = False 
                            start_time = time.time()  # start timer now to power down since no car detected
                    _detState = "nocar"
                    _carDetectCntr = 0

            # to compress measured distance into a single digit range
            DispMin = 0 # min value to display 
            DispMax = 9 # max value to display
            OldRange = (_sensorMaxF - nom_parked_Front)
            NewRange = (DispMax - DispMin)  
            dispNum = (((Measured_Distance_Front - nom_parked_Front) * NewRange) / OldRange) + DispMin

            if (blink_count > blink_countMax/2):    
                blink_count -= 1
                _blinking = True
            else:
                blink_count -= 1
                _blinking = False

            if (blink_count == 0):
                blink_count = blink_countMax

            if (blinkingCorners and _blinking):
                DrawCorners(offscreen_canvas, _cornerColors[0], _cornerColors[1], _cornerColors[2])
            elif (blinkingCorners and not _blinking): 
                _blinking = False # nop 
            else:
                DrawCorners(offscreen_canvas, _cornerColors[0], _cornerColors[1], _cornerColors[2]) 

            if(_detState == "car" and _powerState == "active"): 
                if (dispNum >3 and dispNum <10 ):
                    _cornerColors=[0,255,0]
                    blinkingCorners = False
                    dispChar = True 
                    DrawUpArrow(offscreen_canvas, 255, 255, 255) # white arrow

                if (dispNum >0 and dispNum <4 ):
                    _cornerColors=[255,255,0]                    
                    blinkingCorners = False                
                    dispChar = True                              
                    DrawUpArrow(offscreen_canvas, 255, 255, 255) # white arrow

                if (dispNum ==0 ):
                    _cornerColors=[0,255,255]                    
                    blinkingCorners = False  
                    DrawP(offscreen_canvas, 0, 255, 0) # '+' in center
                    dispChar = False              
                    DrawRightArrow(offscreen_canvas, 255, 255, 255, True) # white arrow
                    DrawLeftArrow(offscreen_canvas, 255, 255, 255, True) # white arrow
                    DrawUpArrow(offscreen_canvas, 255, 255, 255) # white arrow                                
                    DrawDownArrow(offscreen_canvas, 255, 255, 255) # white arrow                

                if (dispNum <0 ):
                    _cornerColors=[255,0,0]                    
                    blinkingCorners = True
                    DrawX(offscreen_canvas, 255, 0, 0) # red X in center
                    DrawDownArrow(offscreen_canvas, 255, 255, 255) # white arrow                
                    dispChar = False

                if(_powerState == "sleep" ):                    
                    dispNum = -16 # to display a space char
                    offscreen_canvas.Clear()
                    DrawCorners(offscreen_canvas, 255, 255, 255) 

                if(dispChar):
                    len = graphics.DrawText(offscreen_canvas, fontB, 13, 21, graphics.Color(255, 0, 255), chr(48+dispNum))

            if(printDebugInfo):
                print(" Front = "+str(Measured_Distance_Front)+ " (" + _readstatF + ") " + ": Car Detect= "+str(_detState)+": Power State= "+str(_powerState))

            time.sleep(0.05)  
            offscreen_canvas = self.matrix.SwapOnVSync(offscreen_canvas)

            end_time = time.time()
            elapsed_time = (end_time - start_time) 
          
            if ( (elapsed_time > maxOperationTimeParked and _parkedSleepTimerStarted ) or  (elapsed_time > maxOperationTimeExit and _exitSleepTimerStarted )   ):
                displayBrightness = sleep_brightness # to show it is sleeping
                _powerState = "sleep"
                start_time = time.time()  # to reset time 
                _exitSleepTimerStarted = False
                _parkedSleepTimerStarted = False
                _cornerColors=[255,255,255]

            if log_active:
                logtime_end = time.time()
                logtime_elapsed = (logtime_end - logtime_start)
                if logtime_elapsed > log_interval:
                    flog.write(time.strftime("%H:%M:%S", time.localtime()) + " - Front = "+str(Measured_Distance_Front)+ " (" + _readstatF + ") " + ": Car Detect= "+str(_detState)+": Power State= "+str(_powerState) + "\n")
                    logtime_start = time.time()
#==================================================================
#  UPDATE THIS SECTION WITH YOUR MQTT BROKER INFORMATION, 
#  Change topics if desired, or remove/remark this section if not using MQTT

                    # MQTT Publish
                    mqtt_msgs = [{'topic':"parkpi/parking/lastupdate", 'payload':time.strftime("%H:%M:%S", time.localtime())},
                                 {'topic':"parkpi/parking/status", 'payload':_readstatF},
                                 {'topic':"parkpi/parking/frontdist", 'payload':str(Measured_Distance_Front)},
                                 {'topic':"parkpi/parking/cardetect", 'payload':str(_detState)},
                                 {'topic':"parkpi/parking/powerstate", 'payload':str(_powerState)}]
                    # Ignore error on publish fail (e.g. MQTT broker down due to HA restart, etc.)
                    try:
                        publish.multiple(mqtt_msgs, hostname="192.168.1.108", auth={'username':"your_MQTT_user", 'password':"your_MQTT_password"})
                    except:
                        pass
#==================================================================
#------------------------------------------------------------------------------------------------
# end of loop
#------------------------------------------------------------------------------------------------

# Main function
if __name__ == "__main__":
    run_text = RunText()
    if (not run_text.process()):
        run_text.print_help()

#------------------------------------------------------------------------------------------------
# end of code 
#------------------------------------------------------------------------------------------------

