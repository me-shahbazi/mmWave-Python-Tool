# First try and Error
# send Config data and check recived Data
# what happens in first cuple of seconds in Matlab, I guess its all about calculating cfg parameters.

# sourcery skip: use-itertools-product
import serial, time, struct
import serial.tools.list_ports as ports_list
import numpy as np
import pickle

# Statics:
CFGaddress = 'cfgFiles\\vod_vs_18xx_10fps.cfg'
magicWord  = b'\x02\x01\x04\x03\x06\x05\x08\x07'
    # message.body.detObj.header.magicWord[0] = 0x0102;
    # message.body.detObj.header.magicWord[1] = 0x0304;
    # message.body.detObj.header.magicWord[2] = 0x0506;
    # message.body.detObj.header.magicWord[3] = 0x0708;

RangeRows = 64
AzimuthColumns = 48
dataList = []
frameMatrix = np.zeros((RangeRows,AzimuthColumns)).astype(np.uint16)

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
            time.sleep(0.5)
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
print("----------")

# Data Capturing:
MsgHeader_format_str = "IIIIII"
MsgHeader_attributes = [
                "totalPacketLen", "platform", "frameNumber",
                "timeCpuCycles", "numDetectedObj", "numTLVs"
            ]
TLattributes = ["type", "length"]
TLformat = "II"
TLformatSize = struct.calcsize(TLformat)

ShortInt = 'H'
VformatSize = struct.calcsize(ShortInt)

for _ in range(300):
    data = DataReceiver.read(8)
    if data == magicWord:
        print("\t\t\t\t\t----------------------------")
        print("\t\t\t\t\t\t*** New Message: ***")
        bMsgHeader = DataReceiver.read(24)
        tup = struct.unpack(MsgHeader_format_str, bMsgHeader)

        msgHeader = {
            attribute: tup[i]
            for i, attribute in enumerate(MsgHeader_attributes)
        }

        msgHeader["platform"] = hex(msgHeader["platform"])[2:]
        print("Msg Header:\n   ", msgHeader)

        MsgBody = DataReceiver.read(msgHeader["totalPacketLen"]-32) 

        MsgPointer = 0
        # ------------ First TLV: (Type:8) ------------
        bTL = MsgBody[MsgPointer : MsgPointer + TLformatSize]
        MsgPointer += TLformatSize
        tup = struct.unpack(TLformat, bTL)
        TLheader = {
            attribute: tup[i]
            for i, attribute in enumerate(TLattributes)
        }
        print("\nTLV type: ", TLheader["type"])
        print("TLV length: ", TLheader["length"])

        for j in range(RangeRows):
            for i in range(AzimuthColumns):
                bValue = MsgBody[MsgPointer : MsgPointer + VformatSize]
                MsgPointer += VformatSize
                Value = struct.unpack(ShortInt, bValue)[0]
                frameMatrix[RangeRows-1-j][i] = Value

        dataList.append(frameMatrix)
        # There would be some problems with appending
        # if frameMatrix define out of this for loop
        frameMatrix = np.zeros((RangeRows,AzimuthColumns)).astype(np.uint16)

with open('tempData.pkl', 'wb') as f:
    pickle.dump(dataList, f)

print("----------")
# Closing COM ports:
DataReceiver.close()
try:
    CliHandle.write(('sensorStop\n').encode('utf-8'))

    for _ in range(4):
        if response := CliHandle.readline().decode('utf-8').strip():
            print("AWR1843: ", response)
        else:
            print("No response received.")
            break
finally:
    CliHandle.close()
    print("Developed by @me-shahbazi")