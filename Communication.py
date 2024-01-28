import serial, time, struct
import serial.tools.list_ports as ports_list

# Statics:
CFGaddress = 'config\\load.cfg' # Configuration File Address
magicWord = b'\x02\x01\x04\x03\x06\x05\x08\x07'

# Ports Declaration:
print('Searching for ports...')
ports = list(ports_list.comports())
for p in ports:
    print('Found port:', p)
    if 'XDS110 Class Auxiliary Data Port' in str(p):
        Dataport = str(p)[:4]
    elif 'XDS110 Class Application/User UART' in str(p):
        CLIport = str(p)[:4]
DataReceiver = serial.Serial(port=Dataport, baudrate=921600, timeout=5) # Auxiliary Data Port
CliHandle = serial.Serial(port=CLIport, baudrate=115200, timeout=1) # Command Line Interface Handle
print("----------")

# Send configuration commands to the AWR1843 and checking Response
with open(CFGaddress, 'r') as cfgFile:
    print("Configuring RADAR Sensor...\n")
    for command in cfgFile:
        if not command.startswith('%'):
            CliHandle.write((command.strip() + '\n').encode('utf-8')) # Command sent to the AWR1843
            print(command.strip())
            time.sleep(0.1)

            counter = 0
            while True:
                response = CliHandle.readline().decode('utf-8').strip() # Geting Response from it
                print("AWR1843: " , response)
                counter += 1

                if 'Error' in response:
                    break

                if counter > 4:
                    print('!!! Something went wrong !!!')
                    break

                if 'Done' in response: # O.K.
                    #print('\t\tWow! So Good!\n')
                    # print('\n')
                    break

            if 'Error' in response:
                break
print("----------")

# Data Capturing:
MsgHeader_format_str = "IIIIIIII"
MsgHeader_attributes = [
                "version", "totalPacketLen", "platform", "frameNumber",
                "timeCpuCycles", "numDetectedObj", "numTLVs", "subFrameNumber"
            ]
TLattributes = ["type", "length"]
TLformat = "II"

for _ in range(100):
    data = DataReceiver.read(8)
    if data == magicWord:
        print("\t\t\t\t\t\t*** New Message: ***")
        bMsgHeader = DataReceiver.read(32)
        tup = struct.unpack(MsgHeader_format_str, bMsgHeader)

        msgHeader = {
            attribute: tup[i]
            for i, attribute in enumerate(MsgHeader_attributes)
        }
        msgHeader["version"]  = hex(msgHeader["version"])[2:]
        msgHeader["platform"] = hex(msgHeader["platform"])[2:]
        print("Msg Header:\n   ", msgHeader)

        MsgBody = DataReceiver.read(msgHeader["totalPacketLen"]-40) 
        #^^^^^^^^^^     **Very Import -40 Not to lose Any Message**     ^^^^^^^^^^^
        MsgPointer = 0
        #----------------------------------------
        #(1) Frist TLV of Demo Message
        bTL = MsgBody[MsgPointer:MsgPointer+8]
        MsgPointer += 8
        TLtup = struct.unpack(TLformat, bTL)
        TLheader = {
            attribute: TLtup[i]
            for i, attribute in enumerate(TLattributes)
            }
        print("--------------------------------")
        print("TLV type: ", TLheader["type"])
        print("TLV length: ", TLheader["length"])

        numPoints = TLheader["length"]//16
        print("NumPoints: ", numPoints, numPoints == msgHeader["numDetectedObj"])
        dataformat = "ffff"
        dataformatSize = struct.calcsize(dataformat)
        for _ in range(numPoints):
            bData = MsgBody[MsgPointer:MsgPointer+dataformatSize]
            MsgPointer += dataformatSize
            data_attributes = ["x", "y", "z", "velocity"]
            Vtup = struct.unpack(dataformat, bData)
            VData = {attribute: Vtup[i] for i, attribute in enumerate(data_attributes)}
            print("\tVData[x]: ", VData["x"])
            print("\tVData[y]: ", VData["y"])
            print("\tVData[z]: ", VData["z"])
            print("\tVData[velocity]: ", VData["velocity"])

        #----------------------------------------
        #(2) Second TLV of Demo Message
        bTL = MsgBody[MsgPointer:MsgPointer+8]
        MsgPointer += 8
        TLtup = struct.unpack(TLformat, bTL)
        TLheader = {
            attribute: TLtup[i]
            for i, attribute in enumerate(TLattributes)
            }
        print("--------------------------------")
        print("TLV type: ", TLheader["type"])
        print("TLV length: ", TLheader["length"])

        numPoints = TLheader["length"]//4
        print("NumPoints: ", numPoints)
        dataformat = "hh"
        dataformatSize = struct.calcsize(dataformat)
        for _ in range(numPoints):
            bData = MsgBody[MsgPointer:MsgPointer+dataformatSize]
            MsgPointer += dataformatSize
            data_attributes = ["snr", "noise"]
            Vtup = struct.unpack(dataformat, bData)
            VData = {attribute: Vtup[i] for i, attribute in enumerate(data_attributes)}
            print("\tVData[snr]: ", VData["snr"])
            print("\tVData[noise]: ", VData["noise"])
        #----------------------------------------
        #(3) Third TLV of Demo Message
        bTL = MsgBody[MsgPointer:MsgPointer+8]
        MsgPointer += 8
        TLtup = struct.unpack(TLformat, bTL)
        TLheader = {
            attribute: TLtup[i]
            for i, attribute in enumerate(TLattributes)
            }
        print("--------------------------------")
        print("TLV type: ", TLheader["type"])
        print("TLV length: ", TLheader["length"])
        
        numPoints = TLheader["length"]//2
        print("NumPoints: ", numPoints)
        dataformat = "H"
        dataformatSize = struct.calcsize(dataformat)
        for _ in range(numPoints):
            bData = MsgBody[MsgPointer:MsgPointer+dataformatSize]
            MsgPointer += dataformatSize
            data_attributes = ["bin"]
            Vtup = struct.unpack(dataformat, bData)
            VData = {attribute: Vtup[i] for i, attribute in enumerate(data_attributes)}
            # # print("VData[bin]: ", VData["bin"])


print("----------")
# Closing COM ports:
DataReceiver.close()
try:
    CliHandle.write(('sensorStop\n').encode('utf-8'))

    for _ in range(3):
        if response := CliHandle.readline().decode('utf-8').strip():
            print("AWR1843: ", response)
        else:
            print("No response received.")
            break
finally:
    CliHandle.close()
    print("Developed by @me-shahbazi")
