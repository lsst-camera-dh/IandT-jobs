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

    command = 'exposeAcquireAndSave 100 True False ""'
    logger.info(command)
    logger.info(ccs_sub.ts8.synchCommand(1500, command).getResult())

if __name__ == '__main__':
    ccs_sub = CcsSubsystems(subsystems=dict(ts8='ts8'))

    verify_rebs(ccs_sub)

    ccs_sub.ts8.synchCommand(10, "setDefaultImageDirectory %s" % tsCWD)

    setup_sequencer(ccs_sub)

    ccs_sub.ts8.synchCommand(10, "setTestStand TS8")



    # Do exposures for three different image types:  bias, flat, and fe55.
    test_type = 'CONN'
    image_types = ('BIAS', 'FLAT', 'FE55')
    exptimes = (100, 1000, 4000)      # msec (why 100 ms for the bias frame?)
    flag1_vals = (False, True, False) # What do these flags mean?
    flag2_vals = (False, False, True)

    filename_format = "${sensorLoc}_${sensorId}_%s_%s_${seq_info}_${timestamp}.fits"
    for image_type, exptime, flag1, flag2 in \
        zip(image_types, exptimes, flag1_vals, flag2_vals):

        command = "setTestType %s" % test_type
        logger.info(command)
        ccs_sub.ts8.synchCommand(10, command)

        command = "setImageType %s" % image_type
        logger.info(command)
        ccs_sub.ts8.synchCommand(10, command)

        filename = filename_format % (test_type.lower(), image_type.lower())
        command = 'exposeAcquireAndSave %i %s %s "%s"' % \
                  (exptime, flag1, flag2, filename)
        logger.info(command)
        ccs_sub.ts8.synchCommand(100, command)
        logger.info("%s taken with exptime %i ms", image_type, exptime)
