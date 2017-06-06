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

def moveTo(x, y):
    # Aerotech move commands, including setting the speed and ramp rates
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

    # send aerotech controller the SCURVE setting
    chat_cmd = "'SCURVE 7'"  # may need to double nest quotes
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    # send aerotech controller the RAMP RATE setting
    chat_cmd = "'RAMP RATE 10'"  # may need to double nest quotes
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
    #    print('Execution Exception', execution)

    # Set the aerotech stage speed - just a test for the simulator
    # send aerotech controller the RAMP DIST setting
    #chat_cmd = "'RAMP DIST 10'"  # may need to double nest quotes
    #try:
    #    result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    #except ScriptingTimeoutException, timeout:
    #    print('Timeout Exception', timeout)
    #except Exception, execution:
    #    print('Execution Exception', execution)

    # send aerotech controller the RAMP TIME setting
    chat_cmd = "'RAMP TIME 1'"  # may need to double nest quotes
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    # send aerotech controller the speed setting
    chat_cmd = "'F 100'"  # may need to double nest quotes
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    # Define the relative move to get to target position from the current
    diff = [x - current[0], y - current[1], 0.0]  # assume no move in z
    print("moveInc_xyz")
    try:
        result = positioner.synchCommand(100, "moveInc_xyz", diff[0], diff[1], diff[2])
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)
    print("after moveInc_xyz")

    #printf "new axis: %s\nnew coords: %s\n",join(' ',@{$new_axis_list}),join(' ',@{$new_coord_list});

def planestatus(flag, pause):
    # flag is used as a bit-wise mask; pause is a wait in seconds

    # query aerotech controller about the motion status
    chat_cmd = "'PLANESTATUS 0'"  # may need to double nest quotes
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    if pause > 0:
        print("pausing in planestatus")
        time.sleep(pause)

    # Parse the result returned by the aerotech controller
    check = (result.getResult()[0] == '%')
    if not(check):  # if the first character is not a %
        return 1

    status = int(result.getResult()[1])  # the next character is to be interpreted
    if flag == 0:
        return status
    else:
        return status & flag  # This is a bitwise -and-

# Define headings for the output file
aero_cols = ["aero_x ", "aero_y ", "aero_z "]
keyence_cols = ["key_z1 ", "key_z2 "]
bookkeeping_cols = ["timestamp ", "label "]
output_cols = aero_cols + keyence_cols + bookkeeping_cols

# define a dictionary of dictionaries for measurement and positioning
#meas = {"target"  : "metrology/Measurer",
#        "channel" : "keyenceChat",
#        "dlog"    : \&kchatter,
#        "save_pars" : "this.txt",
#        "startup" : 1}
#posn = {"target"  : "metrology/Positioner",
#        "channel" : "aerotechChat",
#        "dlog"    : \&achatter,
#        "startup" : 1}
#instr = {"meas": meas, "posn": posn}

# more setup [combine command strings]
#instr['meas']['prepend'] = instr['meas']['target'] + ' ' + 
#                           instr['meas']['channel'] 
#instr['posn']['prepend'] = instr['posn']['target'] + ' ' + 
#                           instr['posn']['channel']

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
chat_cmd = "'WAIT MODE NOWAIT'" 
try:
    result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
except ScriptingTimeoutException, timeout:
    print('Timeout Exception', timeout)
except Exception, execution:
    print('Execution Exception', execution)

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
for head in range(1,3):
    try:
        chat_cmd = "'SW,OC,%2.2d,0,%1d'" % head, keyence_filter_model_ix
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
fout = open(output_file, "a")
fout.write('# measurement begun at local time ' + time.asctime())
fout.write('# input file: ' + input_file)

# Add code to retrieve the configuration parameters

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
