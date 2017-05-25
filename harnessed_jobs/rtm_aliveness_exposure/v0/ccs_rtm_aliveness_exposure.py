"""
Exposure aliveness tests script, based on Homer's
harnessed-jobs/T08/rebalive_exposure/ccseorebalive_exposure.py script.
"""
import sys
import logging
from org.lsst.ccs.scripting import CCS
from ccs_scripting_tools import CcsSubsystems
from ts8_utils import set_ccd_info

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

def verify_rebs(ts8, logger=logger):
    "List the REBs that are attached."
    rebs = ts8.synchCommand(10, "getREBDeviceNames").getResult()
    logger.info("%i REBs found:", len(rebs))
    for reb in rebs:
        logger.info("  %s", reb)

def setup_sequencer(ts8, sequence_file=sequence_file, nclears=10,
                    logger=logger):
    "Set up the sequencer and execute a zero-second exposure."
    logger.info("Set up the sequencer and execute a zero-second exposure:")

    command = "loadSequencer %s" % sequence_file
    ts8.synchCommand(90, command)

    command = "setSequencerStart Clear"
    ts8.synchCommand(10, command)

    for iclear in range(nclears):
        command = "startSequencer"
        logger.info("%i", iclear)
        ts8.synchCommand(10, command)
        command = "waitSequencerDone 5000"
        ts8.synchCommand(10, command)

    command = 'exposeAcquireAndSave 100 False False ""'
    logger.info(ts8.synchCommand(300, command).getResult())

if __name__ == '__main__':
    if subsystems is None:
        subsystems = dict(ts8='ts8', rebps='ccs-rebps')

    ccs_sub = CcsSubsystems(subsystems=subsystems, logger=logger)

    verify_rebs(ccs_sub.ts8)

    set_ccd_info(ccs_sub, ccd_names, logger)

    command = "setDefaultImageDirectory %s/S${sensorLoc}" % tsCWD
    ccs_sub.ts8.synchCommand(10, command)

    setup_sequencer(ccs_sub.ts8)

    ccs_sub.ts8.synchCommand(10, 'setRunNumber %s' % RUNNUM)
    ccs_sub.ts8.synchCommand(10, "setTestStand TS8")

    test_type = 'CONN'
    image_type = 'FLAT'

    command = "setTestType %s" % test_type
    ccs_sub.ts8.synchCommand(10, command)

    command = "setImageType %s" % image_type
    ccs_sub.ts8.synchCommand(10, command)

    openShutter = False
    actuateXED = False
    filename_format = "${CCDSerialLSST}_${testType}_${imageType}_%04d_${RunNumber}_${timestamp}.fits"

    # Take frames for three different exposure times.
    exptimes = (100, 1000, 4000)
    for exptime in exptimes:
        filename = filename_format % exptime
        command = 'exposeAcquireAndSave %i %s %s "%s"' % \
                  (exptime, openShutter, actuateXED, filename)
        ccs_sub.ts8.synchCommand(100, command)
        logger.info("%s taken with exptime %i ms", image_type, exptime)
