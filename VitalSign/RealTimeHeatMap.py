# RealTime Heatmap
# Next Step: Calculate the sum of values in scanning Windows to find deferences between frames or high Reflection area in a single frame
# Next Step: Put more data into the Heatmap Matrix like color - frames
# Next Step: AI machine vision
# sourcery skip: use-itertools-product
import serial, time, struct
import serial.tools.list_ports as ports_list
import cv2
import numpy as np

# Statics:
CFGaddress = 'cfgFiles\\vod_vs_18xx_10fps.cfg'
magicWord  = b'\x02\x01\x04\x03\x06\x05\x08\x07'
magicWordLen = len(magicWord)
#____________________________________________
RangeRows = 64
AzimuthColumns = 48
dispW = 480
dispH = 640
frameMatrix = np.zeros((RangeRows,AzimuthColumns)).astype(np.uint16)
grayImg     = np.zeros((RangeRows,AzimuthColumns)).astype(np.uint8)
#____________________________________________

MsgHeader_format_str = "IIIIII"
MsgHeader_size = struct.calcsize(MsgHeader_format_str)
MsgHeader_attributes = [
                "totalPacketLen", "platform", "frameNumber",
                "timeCpuCycles", "numDetectedObj", "numTLVs"
            ]
TLattributes = ["type", "length"]
TLformat = "II"
TLformatSize = struct.calcsize(TLformat)

ShortInt = 'H'
VformatSize = struct.calcsize(ShortInt)
#____________________________________________
# Ports Declaration:
print('Searching for ports...')
ports = list(ports_list.comports())
for p in ports:
    print('Found port:', p)
    if 'XDS110 Class Auxiliary Data Port' in str(p):
        Dataport = str(p)[:4]
    elif 'XDS110 Class Application/User UART' in str(p):
        CLIport = str(p)[:4]
DataReceiver = serial.Serial(port=Dataport, baudrate=921600, timeout=1) # Auxiliary Data Port
CliHandle    = serial.Serial(port=CLIport , baudrate=115200, timeout=1) # Command Line Interface Handle
print('Ports connected successfully.')


# Send configuration commands to the AWR1843 and checking Response
with open(CFGaddress, 'r') as cfgFile:
    print("\nConfiguring RADAR Sensor...")
    for command in cfgFile:
        if not command.startswith('%'):
            time.sleep(0.2)
            print('\n' + command.strip())
            CliHandle.write((command.strip() + '\n').encode('utf-8')) # Command sent to the AWR1843

            counter = 0
            while True:
                response = CliHandle.readline().decode('utf-8').strip() # Geting Response from it
                print("AWR1843: " , response)
                counter += 1

                if 'Error' in response:
                    afterError = CliHandle.readline().decode('utf-8').strip() # Geting Response from it
                    print("AWR1843: " , afterError)
                    break

                if counter > 5:
                    print('!!! Something went wrong !!!')
                    break

                if 'Done' in response: # O.K.
                    print("OK!")
                    break

            if 'Error' in response:
                break
    print("----------\n")

for _ in range(500):
    data = DataReceiver.read(magicWordLen)
    if data == magicWord:

        bMsgHeader = DataReceiver.read(MsgHeader_size)
        tup = struct.unpack(MsgHeader_format_str, bMsgHeader)
        msgHeader = {
            attribute: tup[i]
            for i, attribute in enumerate(MsgHeader_attributes)
        }
        msgHeader["platform"] = hex(msgHeader["platform"])[2:]
        # print("Message Header:\n", msgHeader)

        MsgBody = DataReceiver.read(msgHeader["totalPacketLen"]-(magicWordLen + MsgHeader_size))
        MsgPointer = 0

        bTL = MsgBody[MsgPointer : MsgPointer + TLformatSize]
        MsgPointer += TLformatSize
        tup = struct.unpack(TLformat, bTL)
        TLheader = {
            attribute: tup[i]
            for i, attribute in enumerate(TLattributes)
        }
        # print("first TLV Type-Length: ", TLheader)

# ----------------------------------------------------------------
        # Interpreting Heatmap Data:
        for j in range(RangeRows):
            for i in range(AzimuthColumns):
                bValue = MsgBody[MsgPointer : MsgPointer + VformatSize]
                MsgPointer += VformatSize
                Value = struct.unpack(ShortInt, bValue)[0]
                frameMatrix[RangeRows-1-j][i] = Value    

        # Scaling:
        NearIgnore = RangeRows - 4
        frameMax = np.max(frameMatrix[:NearIgnore])
        scale = (frameMax // 255) + 1
        # print("Scaling Parameter: ", scale, frameMax)

        # Creating standard frame:
        for row in range(NearIgnore):
            for col in range(len(grayImg[0])):
                grayImg[row][col] = frameMatrix[row][col]//scale                
                if grayImg[row][col] >= (205): # 0.8*255 = 205
                    grayImg[row][col] = 255
                elif grayImg[row][col] < (20):
                    grayImg[row][col] = 0

        # Showing Output:
        reSizedImg = cv2.resize(grayImg,(dispW,dispH), interpolation=cv2.INTER_NEAREST)
        cv2.imshow('GrayScaled Image', reSizedImg)
# ----------------------------------------------------------------

        # Since we don't use append method in this script,so there is no need for:
        # frameMatrix = np.zeros((RangeRows,AzimuthColumns)).astype(np.uint16)
    
    cv2.waitKey(1) # Do not remove this line, why is that happening?
    # why open CV does not show out put when I remove cv2.waitKey(1) at the end of loop?

cv2.destroyAllWindows()
# Closing COM ports:
DataReceiver.close()
try:
    CliHandle.write(('sensorStop\n').encode('utf-8'))

    for _ in range(4):
        if response := CliHandle.readline().decode('utf-8').strip():
            print("AWR1843: ", response)
        else:
            print("No other response received.")
            break
finally:
    CliHandle.close()
    print("Developed by @me-shahbazi")