"""
Exposure aliveness tests script, based on Homer's
harnessed-jobs/T08/rebalive_exposure/ccseorebalive_exposure.py script.
"""
import sys
import logging
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

    command = "startSequencer"
    for iclear in range(nclears):
        logger.info("%i %s", iclear, command)
        logger.info(ccs_sub.ts8.synchCommand(10, command).getResult())

    command = 'exposeAcquireAndSave 0 True False ""'
    logger.info(command)
    logger.info(ccs_sub.ts8.synchCommand(1500, command).getResult())

if __name__ == '__main__':
    ccs_sub = CcsSubsystems(subsystems=dict(ts8='ts8'))

    verify_rebs(ccs_sub)

    ccs_sub.ts8.synchCommand(10, "setDefaultImageDirectory %s" % tsCWD)

    setup_sequencer(ccs_sub)

    ccs_sub.ts8.synchCommand(10, "setTestStand TS8")

    test_type = 'CONN'
    image_type = 'FLAT'
    openShutter = False
    actuateXED = False
    filename_format = "${sensorLoc}_${sensorId}_%s_%s_%04i_${timestamp}.fits"

    # Take frames for three different exposure times.
    exptimes = (0, 1000, 4000)
    for exptime in exptimes:

        command = "setTestType %s" % test_type
        logger.info(command)
        ccs_sub.ts8.synchCommand(10, command)

        command = "setImageType %s" % image_type
        logger.info(command)
        ccs_sub.ts8.synchCommand(10, command)

        filename = filename_format % (test_type.lower(), image_type.lower(),
                                      exptime)
        command = 'exposeAcquireAndSave %i %s %s "%s"' % \
                  (exptime, openShutter, actuateXED, filename)
        logger.info(command)
        ccs_sub.ts8.synchCommand(100, command)
        logger.info("%s taken with exptime %i ms", image_type, exptime)
