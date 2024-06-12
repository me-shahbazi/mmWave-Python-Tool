# This Program developed in order to provide easy access to Ti Radar Sensor
import serial, time, struct
import serial.tools.list_ports as ports_list
import cv2
import numpy as np

class TiVODSensor():
    CFGaddress = 'cfgFiles\\vod_vs_18xx_10fps.cfg'
    magicWord  = b'\x02\x01\x04\x03\x06\x05\x08\x07'
    magicWordLen = len(magicWord)

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

    dataList = []
    RangeRows = 64
    AzimuthColumns = 48
    dispW = 480
    dispH = 640
    frameMatrix = np.zeros((RangeRows,AzimuthColumns)).astype(np.uint16)
    grayImg     = np.zeros((RangeRows,AzimuthColumns)).astype(np.uint8)

    def __init__(self):
        self.Connect()

    def Connect(self):
        print('Searching for ports...')
        ports = list(ports_list.comports())
        for p in ports:
            print('Found port:', p)
            if 'XDS110 Class Auxiliary Data Port' in str(p):
                Dataport = str(p)[:4]
            elif 'XDS110 Class Application/User UART' in str(p):
                CLIport = str(p)[:4]
        self.DataReceiver = serial.Serial(port=Dataport, baudrate=921600, timeout=1) # Auxiliary Data Port
        self.CliHandle    = serial.Serial(port=CLIport , baudrate=115200, timeout=1) # Command Line Interface Handle
        print('Ports connected successfully.')

    def closeConnection(self):
        self.DataReceiver.close()
        try:
            self.CliHandle.write(('sensorStop\n').encode('utf-8'))

            for _ in range(4):
                if response := self.CliHandle.readline().decode('utf-8').strip():
                    print("AWR1843: ", response)
                else:
                    print("No response received.")
                    break
        finally:
            self.CliHandle.close()
            print("Developed by @me-shahbazi")

    def Configure(self, CFGaddress):
        with open(CFGaddress, 'r') as cfgFile:
            print("\nConfiguring RADAR Sensor...")
            for command in cfgFile:
                if not command.startswith('%'):
                    time.sleep(0.5)
                    print('\n' + command.strip())
                    self.CliHandle.write((command.strip() + '\n').encode('utf-8')) # Command sent to the AWR1843
                    
                    counter = 0
                    while True:
                        response = self.CliHandle.readline().decode('utf-8').strip() # Geting Response from it
                        print("AWR1843: " , response)
                        counter += 1

                        if 'Error' in response:
                            afterError = self.CliHandle.readline().decode('utf-8').strip() # Geting Response from it
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
    
    def parse(self, rep):
        for _ in range(rep):
            data = self.DataReceiver.read(self.magicWordLen)
            if data == self.magicWord:
                print("\t\t\t\t\t----------------------------")
                print("\t\t\t\t\t\t*** New Message: ***")
                bMsgHeader = self.DataReceiver.read(self.MsgHeader_size)
                tup = struct.unpack(self.MsgHeader_format_str, bMsgHeader)

                msgHeader = {
                    attribute: tup[i]
                    for i, attribute in enumerate(self.MsgHeader_attributes)
                }

                msgHeader["platform"] = hex(msgHeader["platform"])[2:]
                print("Msg Header:\n   ", msgHeader)

                MsgBody = self.DataReceiver.read(msgHeader["totalPacketLen"]-(self.magicWordLen + self.MsgHeader_size)) 

                MsgPointer = 0
                # ------------ First TLV: (Type:8) ------------
                bTL = MsgBody[MsgPointer : MsgPointer + self.TLformatSize]
                MsgPointer += self.TLformatSize
                tup = struct.unpack(self.TLformat, bTL)
                TLheader = {
                    attribute: tup[i]
                    for i, attribute in enumerate(self.TLattributes)
                }
                print("--------------------------------")
                print("TLV type: ", TLheader["type"])
                print("TLV length: ", TLheader["length"])

                for j in range(self.RangeRows):
                    for i in range(self.AzimuthColumns):
                        bValue = MsgBody[MsgPointer : MsgPointer + self.VformatSize]
                        MsgPointer += self.VformatSize
                        Value = struct.unpack(self.ShortInt, bValue)[0]
                        self.frameMatrix[self.RangeRows-1-j][i] = Value


                # ------------ Second TLV: (Type:9) ------------
                bTL = MsgBody[MsgPointer : MsgPointer + self.TLformatSize]
                MsgPointer += self.TLformatSize
                tup = struct.unpack(self.TLformat, bTL)
                TLheader = {
                    attribute: tup[i]
                    for i, attribute in enumerate(self.TLattributes)
                }
                print("--------------------------------")
                print("TLV type: ", TLheader["type"])
                print("TLV length: ", TLheader["length"])
                
                MsgPointer += TLheader["length"]
                
                # ------------ Third TLV: (Type:10) ------------
                bTL = MsgBody[MsgPointer : MsgPointer + self.TLformatSize]
                MsgPointer += self.TLformatSize
                tup = struct.unpack(self.TLformat, bTL)
                TLheader = {
                    attribute: tup[i]
                    for i, attribute in enumerate(self.TLattributes)
                }
                print("--------------------------------")
                print("TLV type: ", TLheader["type"])
                print("TLV length: ", TLheader["length"])
                MsgPointer += TLheader["length"]
                print("MsgPointer = ", MsgPointer)

                self.Display()


    def Scale(self):
        pass

    def Display(self):
        reSizedImg = cv2.resize(self.frameMatrix,(self.dispW,self.dispH), interpolation=cv2.INTER_NEAREST)
        cv2.imshow('GrayScaled Image', reSizedImg)

        # Save frame matrix:
        # self.dataList.append(self.frameMatrix)
        # There would be some problems with appending
        # if frameMatrix define out of this for loop SO:
        # self.frameMatrix = np.zeros((self.RangeRows,self.AzimuthColumns)).astype(np.uint16)
        
        cv2.waitKey(1) # Do not remove this line, why is that happening?
        # why open CV does not show out put when I remove cv2.waitKey(1) at the end of loop?
    

if __name__ == '__main__':
    myRadar = TiVODSensor()
    myRadar.Configure('cfgFiles\\vod_vs_18xx_10fps.cfg')
    myRadar.parse(100)
    myRadar.closeConnection()
    cv2.destroyAllWindows()