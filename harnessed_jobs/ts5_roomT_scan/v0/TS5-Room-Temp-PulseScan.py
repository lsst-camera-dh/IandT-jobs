# This is intended to be a Jython implementation of Andy Rasmussen's
# pulse scan version of ts5_dlog.perl

from org.lsst.ccs.scripting import *
from java.lang import Exception
import sys
import time

CCS.setThrowExceptions(True)

input_file = '/Users/digel/Desktop/Documents/LSSTCamera/TS5/metro_scan_stuff2/ts5_update_pulse-scans/try_0.5_fidreref.t'

output_file = 'output_PulseScan.txt'
nsample = 10  # repeat count for REREF scan points

#Create the equivalent of a CCS subsystem for scripting
metrology = CCS.attachSubsystem("metrology");
positioner = CCS.attachSubsystem("metrology/Positioner")
measurer = CCS.attachSubsystem("metrology/Measurer")

def aeroHandler(chat_cmd):
    # Wraps aerotechChat commands to the Aerotech controller
    try:
        result = positioner.synchCommand(100, "aerotechChat", posnquot(chat_cmd))
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

def keyenceHandler(chat_cmd):
    # Wraps keyenceChat commands to the Keyence controller
    try:
        result = measurer.synchCommand(100, "keyenceChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

def moveTo(x, y):
    # Commands to move the Aerotech, including setting the speed and ramp rates

    # Get current position
    try:
        result = positioner.synchCommand(100, "getPos_xyz")
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    current = result.getResult()  # a 3-element array of doubles
    print("current: " + str(current[0]) + " " + str(current[1]) + " "
        + str(current[2]) + " target: " + str(x) + ', ' + str(y))

    # Send a series of settings
    aeroHandler("SCURVE 7")
    aeroHandler("RAMP RATE 10")
    aeroHandler("RAMP DIST 10")
    aeroHandler("RAMP TIME 1")

    # Send a 'manual' relative move command (no move in z)
    # The formatting below potentially leaves extra blank spaces
    #aeroHandler("'LINEAR X %13.7f Y %13.7f F 10'" % (x - current[0], y - current[1]))
    chat_cmd = posnquot("LINEAR X %13.7f Y %13.7f F 10" % (x - current[0], y - current[1]))

    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)
    print("after LINEAR, returned:")
    print(result.getResult())

def planestatus(flag, pause):
    # flag is used as a bit-wise mask; pause is a wait in seconds

    # query aerotech controller about the motion status
    aeroHandler("PLANESTATUS 0")

    if pause > 0:
        time.sleep(pause)

    # Parse the result returned by the aerotech controller
    check = (result.getResult()[0] == '%')
    if not(check):  # if the first character is not a %
        return True  # The response was not understandable; pretend it means
                     # that the stage is still moving

    status = int(result.getResult()[1:])  # the next character is to be interpreted
    if flag == 0:
        return status == 1  # True if the Aerotech returned '%1'
    else:
        return (status & flag) == 1  # The & is bitwise -and-

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

def set_aero_register(rix, val):
    chat_cmd = posnquot("DGLOBAL(%d)=%g" % (rix, val))
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    return result.getResult()

def get_aero_register(rix):
    chat_cmd = posnquot("DGLOBAL(%d)" % rix)
    try:
        result = positioner.synchCommand(100, "aerotechChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    return result.getResult()

def ts5_pulsescan(xstart, ystart, xend, yend, numpoints, dc, slewspeed=100, ramprate=2.5, scurve=15, pwidth=0.010):
    # populate Aerotech register variables with appropriate parameters
    set_aero_register(100, dwelltime)
    set_aero_register(101, xstart)
    set_aero_register(102, ystart)
    set_aero_register(103, xend)
    set_aero_register(104, yend)
    set_aero_register(105, numpoints)
    set_aero_register(106, dc)
    set_aero_register(107, slewspeed)
    set_aero_register(108, ramprate)
    set_aero_register(109, scurve)
    set_aero_register(110, pwidth)

    # Initialize keyence acquisition
    try:
        chat_cmd = posnquot("AQ,AS")
        result = measurer.synchCommand(100, "keyenceChat", chat_cmd)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    # Call coord_slew.bcx
    exequot("pulse_scan.bcx")

    n1 = 0
    tstart = -1
    while n1 < numpoints:
        # Wait until finished moving; read number of samples read
        try:
            result = measurer.synchCommand(100, "AN")
        except ScriptingTimeoutException, timeout:
            print('Timeout Exception', timeout)
        except Exception, execution:
            print('Execution Exception', execution)

        pieces = result.getResult().split(',')

        n1, n2 = int(pieces[2]), int(pieces[3])
        time.sleep(1.)  # while counting only interrogate @1 Hz

        # capture approximate time of first data latch
        if tstart == -1 and n1 > 0:
            tstart = time.time()  # current time

    # capture time of final data latch
    tstop = time.time()

    # stop acquisition
    try:
        result = measurer.synchCommand(100, "AP")
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)

    # read out the values
    try:
        result = measurer.synchCommand(100, "AO,01")
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)
    z1 = result.getResult().split(',')

    try:
        result = measurer.synchCommand(100, "AO,02")
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)
    z2 = result.getResult().split(',')
    
    # read in the aerotech captured positions after move is complete
    # First wait until the stage has stopped
    moving = True
    flag = 1  # what is this?  Something to do with planestatus
    while moving:
        moving = planestatus(flag, 0.05)

    use_aero_coordinates = 0

    a = 1.0/(numpoints*(1 + (1 - 1.0/numpoints)*(1.0/dc-1)))
    b = a*(1/dc - 1)
    aplusb = floor((a+b)*2000+0.5)/2000.0

    timestamp = []
    for ix in [0, numpoints]:
         scale = ix*aplusb + 0.5*a
         timestamp.append("%13.7f" % tstart + scale*(tend - tstart))

    xlist = []
    ylist = []
    if use_aero_coordinates:
        doffset = 150
        for ix in [0, numpoints]:
            r1 = get_aero_register(doffset + 2*ix + 0)
            r2 = get_aero_register(doffset + 2*ix + 1)
            xlist.append(r1)
            ylist.append(r2)
    else:
        # compute the positions based on xstart, ystast, xend, yend,
        # numpoints, and dc
        dx = []
        dy = []
        # awkward subtraction of lists; numpy is not available
        for i in range(len(dx)):
            dx.append(xend[i] - xstart[i])
            dy.append(yend[i] - ystart[i])

        for ix in [0, numpoints]:
            scale = ix*aplusb + 0.5*a
            xlist.append(xstart + scale*dx)
            ylist.append(ystart + scale*dy)

        return xlist, ylist, z1, z2, timestamp

def exequot(programName):
    return posnquot("PROGRAM RUN 1,\"\"" + programName + "\"\"")

def posnquot(command):
    return "\"\'" + command + "\'\""

# Define headings for the output file
aero_cols = ["aero_x ", "aero_y ", "aero_z "]
keyence_cols = ["key_z1 ", "key_z2 "]
bookkeeping_cols = ["timestamp ", "label "]
output_cols = aero_cols + keyence_cols + bookkeeping_cols

# Read the aerotech position
try:
    result = positioner.synchCommand(100, "getPos_xyz")
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


# stop any program that may be running in thread 1
try:
    result = positioner.synchCommand(100, "aerotechChat", posnquot("TASKSTATE 1"))
except ScriptingTimeoutException, timeout:
    print('Timeout Exception', timeout)
except Exception, execution:
    print('Execution Exception', execution)

if result.getResult() == '%3':
    print("Stopping a running program...\t")
    aeroHandler("PROGRAM STOP 1")
    time.sleep(3)
    print("done.\n")

# stop motor movement if moving
if planestatus(1,0.0):
    print("stopping a moving motor...\t")
    time.sleep(0.5)
    aeroHandler("ABORT X Y Z")
    while planestatus(1, 0.05):
        pass
    print("done.\n")

# command aerotech controller to operate in NOWAIT mode
aeroHandler("WAIT MODE NOWAIT")

# and then read parameters queried by GETMODE
for i in range(13):
    try:
        result = positioner.synchCommand(100, "GETMODE %d" % i)
    except ScriptingTimeoutException, timeout:
        print('Timeout Exception', timeout)
    except Exception, execution:
        print('Execution Exception', execution)
    print("got mode %d = %s" % (i, result.getResult()))
    
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
keyence_sample_time_ix = 5
keyence_filter_model_ix = 6
keyence_out_sync_ix = 1
keyence_out_storage_ix = 1
keyence_storagemode_ix = 10
keyence_trigger_ix = 0
nmax_stored_samples = 50000

keyenceHandler("Q0")
keyenceHandler("SW,CA,%1d" % keyence_sample_time_ix)
keyenceHandler("SW,CF,%07d,%2.2d" % (keyence_storagemode_ix, nmax_stored_samples))
for head in [1,2]:
    keyenceHandler("SW,OE,M,%2.2d,%1d" % (head, keyence_trigger_ix))
    keyenceHandler("SW,OC,%2.2d,0,%1d" % (head, keyence_filter_model_ix))
    keyenceHandler("SW,OJ,%2.2d,%1d" % (head, keyence_out_sync_ix))
    keyenceHandler("SW,OK,%2.2d,%1d" % (head, keyence_out_storage_ix))

keyenceHandler("R0")

dwelltime = keyence_filter_model[str(keyence_filter_model_ix)]*keyence_sample_time[str(keyence_sample_time_ix)]

print "dwelltime:  " + str(dwelltime)

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
fout.write('aero_x  aero_y  aero_z  key_z1  key_z2  timestamp       label')

start_time = time.time()

# Open the file that has the scan positions and labels
label = ' '
f = open(input_file, 'r')

coord = 0  # flag for reading coordinate specifications; this is a bit
           # awkward but it allows the file to be read using the
           # 'for line in f:' approach
label = ''
xref = [0, 0, 0]
yref = [0, 0, 0]

for line in f:
    # parse the line
    # if the line contains TF copy it to the output as a transformation spec
    if line.find('TF') > 0:
        fout.write('# ' + line[1:])

    pieces = line.split()
    if pieces[1] == 'part':
        label = pieces[4]  # label to use for the next measurements
    elif pieces[1] == 'SCAN':
        numpoints = int(pieces[2][2:])
        dc = float(pieces[3][3:])
    else:
        if label == 'REREF':
            # Read the next three lines as the coordinates of the reference
            # measurements
            if coord < 2:
                xref[coord], yref[coord] = float(pieces[0]), float(pieces[1])
                coord += 1
            else:
                xref[coord], yref[coord] = float(pieces[0]), float(pieces[1])
                coord = 0

                # Make -nsample- measurements of each of these points
                for i in range(3):
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
                        fout.write('%f %f %f %f %f %f %s' % (aero_pos[0],
                                                             aero_pos[1],
                                                             aero_pos[2],
                                                             key_pos[0],
                                                             key_pos[1],
                                                             delta_time, 
                                                             label))

        else:
            # Read the next two lines as the starting and ending x, y 
            # coordinates of the current scan line
            if coord == 0:
                xstart, ystart = float(pieces[0]), float(pieces[1])
                coord += 1
            else:
                xend, yend = float(pieces[0]), float(pieces[1])
                coord = 0

            print("label=%s n=%d dutycycle=%f start=(%f, %f) end=(%f, %f)\n" % (label, numpoints, dc, xstart, ystart, xend, yend))
            try:
                result = positioner.synchCommand(100, "getPos_z")
            except ScriptingTimeoutException, timeout:
                print('Timeout Exception', timeout)
            except Exception, execution:
                print('Execution Exception', execution)
            zpos = result.getResult()

            # Now execute this scan line
            xlist, ylist, z1, z2, timestamp = ts5_pulsescan(xstart, ystart, xend, yend, numpoints, dc)

            # Append the results to the output file
            for i in range(len(xlist)):
                fout.write('%f %f %f %f %f %f %s' % (xlist[i], 
                                                  ylist[i],
                                                  zpos,
                                                  z1[i],
                                                  z2[i],
                                                  timestamp[i],
                                                  label))

f.close()

# Write closing line
fout.write("# measurement completed at local time " + time.asctime())
fout.close()
