import serial, time
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
CliHandle = serial.Serial(port=CLIport, baudrate=115200, timeout=2) # Command Line Interface Handle

print("----------")
# Send configuration commands to the AWR1843 and checking Response
with open(CFGaddress, 'r') as cfgFile:
    print("\nConfiguring RADAR Sensor...\n")
    for command in cfgFile:
        if not command.startswith('%'):
            CliHandle.write((command.strip() + '\n').encode('utf-8')) # Command sent to the AWR1843
            print(command.strip())
            time.sleep(0.1)

            counter = 0
            while True:
                response = CliHandle.readline().decode('utf-8').strip() # Geting Response from it
                print("AWR1843: " , response)
                #time.sleep(0.1)
                counter += 1

                if 'Error' in response:
                    break
                
                if counter > 4:
                    print('!!! Something went wrong !!!')
                    break

                if 'Done' in response: # O.K.
                    #print('\t\tWow! So Good!\n')
                    print('\n')
                    break
            
            if 'Error' in response:
                break

print("----------")
# Data Capturing:
while True:
    try:
        data = DataReceiver.read(8)
        if data == magicWord:
            print("*** New Message: ***")
            header = DataReceiver.read(40)
            print("The header is: ", header)
            break
    finally:
        break

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
