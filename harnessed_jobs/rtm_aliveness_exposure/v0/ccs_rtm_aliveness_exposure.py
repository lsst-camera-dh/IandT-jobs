"""
Exposure aliveness tests script, based on Homer's
harnessed-jobs/T08/rebalive_exposure/ccseorebalive_exposure.py script.
"""
import os
import stat
import sys
import time
import shutil
import logging
import subprocess
from org.lsst.ccs.scripting import *
import java.lang
#import eolib

CCS.setThrowExceptions(True);

logging.basicConfig(format="%(message)s",
                    level=logging.DEBUG,
#                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

class CcsSubsystems(object):
    def __init__(self, subsystems=None):
        if subsystems is None:
            subsystems = dict(ts8='ts8', rebps='ccs-rebps')
        for key, value in subsystems.items():
            self.__dict__[key] = CCS.attachSubsystem(value)

#for item in sys.path:
#    logger.info(item)

ccs_sub = CcsSubsystems(subsystems=dict(ts8='ts8',
                                        rebps='ccs-rebps',
                                        ts='ts',
                                        bias='ts/Bias',
                                        pd='ts/PhotoDiode',
                                        mono='ts/Monochromator'))

wl = 500.
for itry in range(3):
    try:
        rwl = ccs_sub.mono.synchCommand(60, "setWaveAndFilter %f" % wl).getResult()
        logger.info("rwl = %s", rwl)
        ccs_sub.ts8.synchCommand(10, "setHeader MonochromatorWavelength %s"
                                 % rwl)
        ccs_sub.mono.synchCommand(900, "openShutter")
        break
    except java.lang.Exception:
        time.sleep(0.5)
        raise java.lang.Exception("Failed to set monochromator wavelength.")

# Verify data link.
rebs = ""
pstep = 1
istep = 1
test_name = "Step%d_REB_devices" % pstep
logger.info(test_name)
rebs = ccs_sub.ts8.synchCommand(10, "getREBDeviceNames").getResult()
logger.info("# REBs found %i:", len(rebs))
for reb in rebs:
    logger.info("%s", reb)

ccdnames = {}
ccdmanunames = {}
try:
    ccdnames["00"] = CCDS00
    ccdmanunames["00"] = CCDMANUS00
    ccdnames["01"] = CCDS01
    ccdmanunames["01"] = CCDMANUS01
    ccdnames["02"] = CCDS02
    ccdmanunames["02"] = CCDMANUS02
except:
    pass
try:
    ccdnames["10"] = CCDS10
    ccdmanunames["10"] = CCDMANUS10
    ccdnames["11"] = CCDS11
    ccdmanunames["11"] = CCDMANUS11
    ccdnames["12"] = CCDS12
    ccdmanunames["12"] = CCDMANUS12
except:
    pass
try:
    ccdnames["20"] = CCDS20
    ccdmanunames["20"] = CCDMANUS20
    ccdnames["21"] = CCDS21
    ccdmanunames["21"] = CCDMANUS21
    ccdnames["22"] = CCDS22
    ccdmanunames["22"] = CCDMANUS22
except:
    pass

for key, value in ccdnames.items():
    logger.info("%s: %s", key, value)

rafttype = "ITL"
raft = UNITID

logger.info("image directory: %s", tsCWD)

sequence_file = '/lsst/ccs/prod/seq/' + os.path.basename(sequence_file)
logger.info("loading sequencer file: %s", sequence_file)
#ccs_sub.ts8.synchCommand(90, "loadSequencer %s"
#                         % os.path.basename(sequence_file))
ccs_sub.ts8.synchCommand(90, "loadSequencer %s" % sequence_file)

ccs_sub.ts8.synchCommand(10, "setDefaultImageDirectory %s" % tsCWD)

command = "setSequencerStart Clear"
logger.debug(command)
ccs_sub.ts8.synchCommand(10, command).getResult()

command = "startSequencer"
logger.debug(command)
logger.info(ccs_sub.ts8.synchCommand(10, command).getResult())

command = 'exposeAcquireAndSave 100 True False ""'
logger.info(command)
logger.info(ccs_sub.ts8.synchCommand(1500, command).getResult())

#14. Execute a zero-second exposure and readout sequence. Start a timer when the close shutter command executes.
#
#    ts8sub.synchCommand(10,"setDefaultImageDirectory","%s" % (cdir));
#
#    if (True) :
#
#
#        seqcmnd = "setSequencerStart Clear"
#        print ts8sub.synchCommand(10,seqcmnd).getResult();
#        for iclear in range(10):
#            seqcmnd = "startSequencer"
#            print "seqcmnd = (%s)" % seqcmnd
#            print ts8sub.synchCommand(10,seqcmnd).getResult();
#
#        expcmnd1 = 'exposeAcquireAndSave 100 True False ""'
#
#        print "PRE-exposure command: expcmnd1 = ",expcmnd1
#        print ts8sub.synchCommand(1500,expcmnd1).getResult() 
#
#
## <LSST CCD SN>_<test type>_<image type>_<seq. info>_<time stamp>.fits
#
##        fitsfilename = "s${sensorLoc}_r${raftLoc}_${test_type}_${image_type}_${seq_info}_${timestamp}.fits"
#
##        print "fitsfilename = %s" % fitsfilename
#
#        ts8sub.synchCommand(10,"setTestStand","TS6")
#        ts8sub.synchCommand(10,"setTestType","FE55")
#
#        raft = CCDID
##        ts8sub.synchCommand(10,"setRaftLoc",str(raft))
#
#        exptime=0.0
#
#        tm_start = time.time()
#        print "Ready to take image with exptime = %f at time = %f" % (0,tm_start)
#
#        ts8sub.synchCommand(10,"setTestType CONN")
#        ts8sub.synchCommand(10,"setImageType BIAS")
#
## <CCD id>_<test type>_<image type>_<seq. #>_<run_ID>_<time stamp>.fits
#        rply = ts8sub.synchCommand(700,"exposeAcquireAndSave",100,False,False,"${sensorLoc}_${sensorId}_${test_type}_${image_type}_${seq_info}_${timestamp}.fits").getResult()
#
#        tm_end = time.time()
#        print "done taking image with exptime = %f at time = %f" % (0,tm_end)
#        
#        istep = istep + 1
#        rebid = "raft"
#        fp.write("%s| %s \n" % ("Step%d_%s_bias_exposure_t_start" % (istep,rebid),tm_start));
#        fp.write("%s| %s \n" % ("Step%d_%s_bias_exposure_t_end" % (istep,rebid),tm_end));
#
#
#        ts8sub.synchCommand(10,"setTestType CONN")
#        ts8sub.synchCommand(10,"setImageType FLAT")
#
#        exptime=1.000
#        print "Doing 1000ms flat exposure"
#
#        rply = ts8sub.synchCommand(120,"exposeAcquireAndSave",int(exptime*1000),True,False,"${sensorLoc}_${sensorId}_${test_type}_flat_1000ms_${image_type}_${seq_info}_${timestamp}.fits").getResult()
#
#        exptime=4.000
#        print "Doing 4s Fe55 exposure"
#
#        rply = ts8sub.synchCommand(280,"exposeAcquireAndSave",int(exptime*1000),False,True,"${sensorLoc}_${sensorId}_${test_type}_fe55_4000ms_${image_type}_${seq_info}_${timestamp}.fits").getResult()
#
##        exptime=20.000
##
##        rply = ts8sub.synchCommand(280,"exposeAcquireAndSave",int(exptime*1000),True,True,"${sensorLoc}_${sensorId}_${test_type}_20000ms_${image_type}_${seq_info}_${timestamp}.fits").getResult()
#
#
#    fp.close();
#
## satisfy the expectations of ccsTools
#    istate=0;
#    fp = open("%s/status.out" % (cdir),"w");
#    fp.write(`istate`+"\n");
#    fp.write("%s\n" % ts_version);
#    fp.write("%s\n" % ts_revision);
#    fp.write("%s\n" % ts8_version);
#    fp.write("%s\n" % ts8_revision);
#    fp.close();
#
#
#print "rebalive_functionalty test END"
#
#
################################################################################               
## EOgetCCSVersions: getCCSVersions                                                            
#def TS8getCCSVersions(ts8sub,cdir):
#    result = ts8sub.synchCommand(10,"getCCSVersions");
#    ccsversions = result.getResult()
#    ccsvfiles = open("%s/ccsversion" % cdir,"w");
#    ccsvfiles.write("%s" % ccsversions)
#    ccsvfiles.close()
#
#    ssys = ""
#
#    ts8_version = ""
#    ccsrebps_version = ""
#    ts8_revision = ""
#    ccsrebps_revision = ""
#    for line in str(ccsversions).split("\t"):
#        tokens = line.split()
#        if (len(tokens)>2) :
#            if ("ts8" in tokens[2]) :
#                ssys = "ts8"
#            if ("ccs-rebps" in tokens[2]) :
#                ssys = "ccs-rebps"
#            if (tokens[1] == "Version:") :
#                print "%s - version = %s" % (ssys,tokens[2])
#                if (ssys == "ts8") :
#                    ts8_version = tokens[2]
#                if (ssys == "ccs-rebps") :
#                    ccsrebps_version = tokens[2]
#            if (len(tokens)>3) :
#                if (tokens[2] == "Rev:") :
#                    print "%s - revision = %s" % (ssys,tokens[3])
#                    if (ssys == "ts8") :
#                        ts8_revision = tokens[3]
#                    if (ssys == "ccs-rebps") :
#                        ccsrebps_revision = tokens[3]
#
#    return(ts8_version,ccsrebps_version,ts8_revision,ccsrebps_revision)
