"""
Exposure aliveness tests script, based on Homer's
harnessed-jobs/T08/rebalive_exposure/ccseorebalive_exposure.py script.
"""
import sys
import logging
from ts8_utils import set_ccd_info
from org.lsst.ccs.scripting import *

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

class CcsSubsystems(object):
    def __init__(self, subsystems=None):
        if subsystems is None:
            subsystems = dict(ts8='ts8', rebps='ccs-rebps')
        for key, value in subsystems.items():
            self.__dict__[key] = CCS.attachSubsystem(value)

def verify_rebs(ccs_sub, logger=logger):
    rebs = ccs_sub.ts8.synchCommand(10, "getREBDeviceNames").getResult()
    logger.info("%i REBs found:", len(rebs))
    for reb in rebs:
        logger.info("  %s", reb)

def setup_sequencer(ccs_sub, sequence_file=sequence_file, nclears=10,
                    logger=logger):
    logger.info("Set up the sequencer and execute a zero-second exposure:")

    command = "loadSequencer %s" % sequence_file
    logger.info(command)
    logger.info(ccs_sub.ts8.synchCommand(90, command).getResult())

    command = "setSequencerStart Clear"
    logger.info(command)
    logger.info(ccs_sub.ts8.synchCommand(10, command).getResult())

    for iclear in range(nclears):
        command = "startSequencer"
        logger.info("%i %s", iclear, command)
        logger.info(ccs_sub.ts8.synchCommand(10, command).getResult())
        command = "waitSequencerDone 5000"
        logger.info(command)
        logger.info(ccs_sub.ts8.synchCommand(10, command).getResult())

    command = 'exposeAcquireAndSave 100 False False ""'
    logger.info(command)
    logger.info(ccs_sub.ts8.synchCommand(300, command).getResult())

if __name__ == '__main__':
    ccs_sub = CcsSubsystems(subsystems=dict(ts8='ts8', rebps='ccs-rebps'))

    verify_rebs(ccs_sub)

    command = "setDefaultImageDirectory %s/S${sensorLoc}" % tsCWD
    logger.info(command)
    ccs_sub.ts8.synchCommand(10, command)

    setup_sequencer(ccs_sub)

    ccs_sub.ts8.synchCommand(10, "setTestStand TS8")

    test_type = 'CONN'
    image_type = 'FLAT'
    openShutter = False
    actuateXED = False
    filename_format = "${CCDSerialLSST}_${testType}_${imageType}_${SequenceInfo}_${RunNumber}_${timestamp}.fits"

    # Take frames for three different exposure times.
    exptimes = (100, 1000, 4000)
    for exptime in exptimes:
        command = "setSeqInfo %d" % exptime
        logger.info(command)
        ccs_sub.ts8.synchCommand(10, command)

        command = "setTestType %s" % test_type
        logger.info(command)
        ccs_sub.ts8.synchCommand(10, command)

        command = "setImageType %s" % image_type
        logger.info(command)
        ccs_sub.ts8.synchCommand(10, command)

        command = 'exposeAcquireAndSave %i %s %s "%s"' % \
                  (exptime, openShutter, actuateXED, filename_format)
        logger.info(command)
        ccs_sub.ts8.synchCommand(100, command)
        logger.info("%s taken with exptime %i ms", image_type, exptime)
