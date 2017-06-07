# This is intended to be a Jython implementation of Andy Rasmussen's
# ts5_dlog.perl
# It does not yet read and report the controller configurations

from org.lsst.ccs.scripting import *
from java.lang import Exception
import sys
import time

CCS.setThrowExceptions(True)

input_file = '/Users/digel/Desktop/Documents/LSSTCamera/TS5/metro_scan_stuff/reref_spp1_sp1.t'
output_file = 'output.txt'

#Create the equivalent of a CCS subsystem for scripting
metrology = CCS.attachSubsystem("metrology");
positioner = CCS.attachSubsystem("metrology/Positioner")
measurer = CCS.attachSubsystem("metrology/Measurer")

def aeroHandler(chat_cmd):
    # Wraps aerotechChat commands to the Aerotech controller
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

def moveTo(x, y):
    # Commands to move the Aerotech, including setting the speed and ramp rates
    # (may want to set the speed and ramp rates once and for all rather
    #  than every time)

    # get current position
    try:
        result = positioner.synchCommand(100,"getPos_xyz")
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    current = result.getResult()  # a 3-element array of doubles
    print("current: " + str(current[0]) + " " + str(current[1]) + " "
        + str(current[2]) + " target: " + str(x) + ', ' + str(y))

    # Send a series of settings
    aeroHandler("'SCURVE 7'")
    aeroHandler("'RAMP RATE 10'")
    aeroHandler("'RAMP DIST 10'")
    aeroHandler("'RAMP TIME 1'")

    # Send a 'manual' relative move command (no move in z)
    # The formatting below potentially leaves extra blank spaces
    aeroHandler("'LINEAR X %13.7f Y %13.7f F 10'" % (x - current[0], y - current[1]))

    #print("moveInc_xyz")
    #try:
    #    result = positioner.synchCommand(100, "moveInc_xyz", diff[0], diff[1], diff[2])
    #except ScriptingTimeoutException, timeout:
    #    print('Timeout Exception', timeout)
    #except Exception, execution:
    #    print('Execution Exception', execution)
    #print("after moveInc_xyz")

def planestatus(flag, pause):
    # flag is used as a bit-wise mask; pause is a wait in seconds

    # query aerotech controller about the motion status
    aeroHandler("'PLANESTATUS 0'")

    if pause > 0:
        time.sleep(pause)

    # Parse the result returned by the aerotech controller
    check = (result.getResult()[0] == '%')
    if not(check):  # if the first character is not a %
        return 1

    status = int(result.getResult()[1:])  # the next character is to be interpreted
    if flag == 0:
        return status
    else:
        return status & flag  # This is a bitwise -and-

def get_settings():
    # Construct the command string to interrogate the Keyence controller for
    # its settings

    cmds = []

    for output in [1,2]:  # the two heads
        cmds.append("SR,LM,%2.2d" % output)
        cmds.append("SR,HA,M,%2.2d" % output)  # head number assumed equal
        cmds.append("SR,HA,R,%2.2d" % output)  # to output number
        cmds.append("SR,HB,M,%2.2d" % output)
        cmds.append("SR,HB,B,%2.2d" % output)
        cmds.append("SR,HC,N,%2.2d" % output)
        cmds.append("SR,HC,L,%2.2d" % output)
        cmds.append("SR,HE,%2.2d" % output)
        cmds.append("SR,HF,%2.2d" % output)
        cmds.append("SR,HG,%2.2d" % output)
        cmds.append("SR,HI,%2.2d" % output)
        cmds.append("SR,HJ,%2.2d" % output)
        cmds.append("SR,OA,H,%2.2d" % output)
        cmds.append("SR,OA,T,%2.2d" % output)
        cmds.append("SR,OA,C,%2.2d" % output)
        cmds.append("SR,OA,M,%2.2d" % output)
        cmds.append("SR,OB,%2.2d" % output)
        cmds.append("SR,OC,%2.2d" % output)
        cmds.append("SR,OD,%2.2d" % output)
        cmds.append("SR,OE,M,%2.2d" % output)
        cmds.append("SR,OF,%2.2d" % output)
        cmds.append("SR,OG,%2.2d" % output)
        cmds.append("SR,OH,%2.2d" % output)
        cmds.append("SR,OI,%2.2d" % output)
        cmds.append("SR,OJ,%2.2d" % output)
        cmds.append("SR,OK,%2.2d" % output)

    cmds.append("SR,CA")
    cmds.append("SR,CB")
    cmds.append("SR,CD")
    cmds.append("SR,CE")
    cmds.append("SR,CF")

    for output in [1,2]:  # the two heads
        cmds.append("SR,CG,%2.2d" % output)

    cmds.append("SR,CH")
    cmds.append("SR,EE")
    cmds.append("SR,EF")
    cmds.append("SR,EG")
    cmds.append("SR,EH,I")
    cmds.append("SR,EH,M")
    cmds.append("SR,EH,G")
    cmds.append("R0")


    preamble = 'Q0'
    try:
        result = measurer.synchCommand(100, "keyenceChat", preamble)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    # Step through each of the commands, sending them to the Keyence
    # controller
    rets = []
    for cmd in cmds:
        try:
            result = measurer.synchCommand(100, "keyenceChat", cmd)
        except ScriptingTimeoutException, timeout:
            print('Timeout Exception', timeout)
        except Exception, execution:
            print('Execution Exception', execution)
        else:
            # parse the result (assume one line)
            rets.append(result.getResult())

    closeout = 'R0'
    try:
        result = measurer.synchCommand(100, "keyenceChat", closeout)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)
    # controller

    return cmds, rets 


# Define headings for the output file
aero_cols = ["aero_x ", "aero_y ", "aero_z "]
keyence_cols = ["key_z1 ", "key_z2 "]
bookkeeping_cols = ["timestamp ", "label "]
output_cols = aero_cols + keyence_cols + bookkeeping_cols

# Read the aerotech position
try:
    result = positioner.synchCommand(100,"getPos_xyz")
except ScriptingTimeoutException, timeout:
    print('Timeout Exception', timeout)
except Exception, execution:
    print('Execution Exception', execution)

current = result.getResult()  # 3-element array of doubles
print('Aerotech:  ' + str(current[0]) + ' ' + str(current[1]) + ' '
    + str(current[2]))

# Read the keyence distances
try:
    result = measurer.synchCommand(100, "readAll")
except ScriptingTimeoutException, timeout:
    print('Timeout Exception', timeout)
except Exception, execution:
    print('Execution Exception', execution)

zdists = result.getResult()  # 2-element array of doubles
print('Keyence:  ' + str(zdists[0]) + ' ' + str(zdists[1]))

try:
    result = positioner.synchCommand(100, "setSpeed", 1.0)
except ScriptingTimeoutException, timeout:
    print('Timeout Exception', timeout)
except Exception, execution:
    print('Execution Exception', execution)

print("after setSpeed")

# command aerotech controller to operate in NOWAIT mode
aeroHandler("'WAIT MODE NOWAIT'")

# set keyence timing parameters; first define the options
keyence_sample_time = {"cmd" : "SW,CA,%1d",
                       "0" : 2.55e-6,
                       "1" : 5e-6,
                       "2" : 10e-6,
                       "3" : 20e-6,
                       "4" : 50e-6,
                       "5" : 100e-6,
                       "6" : 200e-6,
                       "7" : 500e-6,
                       "8" : 1000e-6}
keyence_filter_model = {"cmd" : "SW,OC,%02d,0,%1d",
                        "0" : 1,
                        "1" : 4,
                        "2" : 16,
                        "3" : 64,
                        "4" : 256,
                        "5" : 1024,
                        "6" : 4096,
                        "7" : 16384,
                        "8" : 65536,
                        "9" : 262144}
# select specific sample time and filter model values
keyence_sample_time_ix = 6
keyence_filter_model_ix = 5
dwelltime = keyence_filter_model[str(keyence_filter_model_ix)]*keyence_sample_time[str(keyence_sample_time_ix)]

print "dwelltime:  " + str(dwelltime)

# Specify these settings using keyenceChat.  For the filter model
# the setting has to be made for both heads (1 and 2)
for head in [1, 2]:
    try:
        chat_cmd = "'SW,OC,%2.2d,0,%1d'" % (head, keyence_filter_model_ix)
        result = measurer.synchCommand(100, "keyenceChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

try:
    chat_cmd = "'SW,CA,%d'" % keyence_sample_time_ix
    result = measurer.synchCommand(100, "keyenceChat", chat_cmd)
except ScriptingTimeoutException, timeout:
    print('Timeout Exception', timeout)
except Exception, execution:
    print('Execution Exception', execution)

# Open the output file and write some headers
fout = open(output_file, "w")
fout.write('# measurement begun at local time ' + time.asctime())
fout.write('# input file: ' + input_file)

# Add code to retrieve the configuration parameters
cmds, rets = get_settings()

print("cmds:")
print(cmds)
print("rets:")
print(rets)

# reverse for popping
cmds.reverse()
rets.reverse()

for index in range(len(cmds)):
    fout.write('# ' + cmds.pop() + ': ' + rets.pop())

fout.write('dat')
#fout.write(string.join(output_cols))
fout.write('aero_x  aero_y  aero_z  key_z1  key_z2  timestamp       label')

ref_time = time.time()

# Open the file that has the scan positions and labels
label = ' '
f = open(input_file, 'r')

for line in f:
    # parse the line
    pieces = line.split()
    if pieces[0] == '!':
        label = pieces[4]  # label to use for the next measurements
    else:
        # interpret the entries as coordinates for the stage
        xpos, ypos = float(pieces[0]), float(pieces[1])
        print(label + ' ' + str(xpos) + ' ' + str(ypos))
        moveTo(xpos, ypos)

        # Now wait until the stage has stopped
        moving = True
        flag = 1  # what is this?  Something to do with planestatus
        while moving:
            moving = planestatus(flag, 0.02)

        try:
            result = positioner.synchCommand(100, "getPos_xyz")
        except ScriptingTimeoutException, timeout:
            print('Timeout Exception', timeout)
        except Exception, execution:
            print('Execution Exception', execution)

        aero_pos = result.getResult()

        # Specify the number of samples to read (10 for the REF
        # surfaces)
        if label == 'REREF':
            nsample = 10
        else:
            nsample = 1

        iter = 0
        while iter < nsample:
            # Wait for -dwelltime-
            time.sleep(dwelltime)

            # Read out the Keyence sensors
            try:
                result = measurer.synchCommand(100, "readAll")
            except ScriptingTimeoutException, timeout:
                print('Timeout Exception', timeout)
            except Exception, execution:
                print('Execution Exception', execution)
            key_pos = result.getResult()

            # get timestamp
            current_time = time.time()
            delta_time = current_time - ref_time

            # Append the results to the output file
            fout.write('%f %f %f %f %f %f' % (aero_pos[0], 
                                              aero_pos[1],
                                              aero_pos[2],
                                              key_pos[0],
                                              key_pos[1],
                                              delta_time) + ' '
                                              + label)
            iter += 1

f.close()

# Write closing line
fout.write("# measurement completed at local time " + time.asctime())
fout.close()
