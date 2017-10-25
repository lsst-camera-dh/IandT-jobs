"""
Power-on aliveness tests script, based on Homer's
harnessed-jobs/T08/rebalive_power/ccseorebalive_power.py script.
"""
import os
import sys
import time
from collections import namedtuple
import logging
import java.lang
from org.lsst.ccs.scripting import CCS
from ccs_scripting_tools import CcsSubsystems
from rebCurrentLimits import RebCurrentLimits
from ts8_utils import get_REB_info

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

def reb_power_on(ccs_sub, rebid, power_line, ccd_type):
    logger = ccs_sub.rebps.logger

    reb_current_limits = RebCurrentLimits(ccs_sub.rebps, ccs_sub.ts8)

    reb_slot = 'REB%d' % rebid
    logger.info("*****************************************************")
    logger.info("Starting power-on procedure for %s (power line %s)",
                reb_slot, power_line)
    logger.info("*****************************************************")

    # Power on the REB using the power-up sequence.
    ccs_sub.rebps.synchCommand(10, 'sequencePower', power_line, True)

    # Check that the power-supply currents are within the limits
    # for each channel.
    reb_current_limits.check_rebps_limits(rebid)

    # Wait 15 seconds for the FPGA to boot, then check currents again.
    time.sleep(15)
    reb_current_limits.check_rebps_limits(rebid)

    # The reb_info namedtuple contains the info for the REB in question.
    # That information can be used in the step 6 & 7 tests.
    reb_info = get_REB_info(ccs_sub.ts8, rebid)

    # Compare the REB hardware serial number to the value in the
    # eTraveler tables for this REB in this raft.
    if reb_info.serialNumber != reb_eT_info[reb_slot].manufacturer_sn:
        raise RuntimeError("REB manufacturer serial number mismatch: %s, %s"
                           % (reb_info.serialNumber,
                              reb_eT_info[reb_slot].manufacturer_sn))

    # TODO: Read and record the firmware version ID, then verify it is
    # the correct version (LCA-10064-A, p.17, step 7).  Currently,
    # there is no reliable way of getting the intended firmware version
    # from the eTraveler.
    logger.info("%s firmware version from CCS: %s", reb_slot,
                reb_info.hwVersion)

    # Check that REB P/S currents match the REB currents from ts8
    # within the comparative limits.
    reb_current_limits.check_comparative_ranges(rebid)

    logger.info("Turn on REB clock and rail voltages.")

    # Load sensor-specific configurations.
    if ccd_type == 'ITL':
        ccs_sub.ts8.synchCommand(10, "loadCategories Rafts:itl")
        ccs_sub.ts8.synchCommand(10, "loadCategories RaftsLimits:itl")
    elif ccd_type == 'E2V':
        ccs_sub.ts8.synchCommand(10, "loadCategories Rafts:e2v")
        ccs_sub.ts8.synchCommand(10, "loadCategories RaftsLimits:e2v")
    else:
        raise RuntimeError("ccs_rtm_aliveness_power_on: Invalid ccd_type, "
                           + ccd_type)

    try:
        outfile = '%s_REB%i_%s_powerOn_aliveness_test_output.txt' \
                  % (UNITID, rebid, RUNNUM)
        outfile = '/'.join((tsCWD, outfile))
        logger.info('Writing powerOn output to %s', outfile)
        with open(outfile, 'w') as output:
            output.write(str(ccs_sub.ts8.synchCommand(900, 'powerOn',
                                                      rebid).getResult()))
        os.chmod(outfile, 0664)
        logger.info("------ %s power-on complete ------\n", reb_slot)
    except java.lang.Exception as eobj:
        logger.info(eobj.message)
        raise eobj

if __name__ == '__main__':
    logger.info("Start time: %f", time.time())

    if subsystems is None:
        subsystems = dict(ts8='ts8', rebps='ccs-rebps')

    ccs_sub = CcsSubsystems(subsystems=subsystems, logger=logger)

    # Assumed mapping of power supply lines to REBs.
    num_lines = 3
    power_lines = {i: i for i in range(num_lines)}

    logger.info("Will attempt to power on and check currents for")
    for rebid, power_line in power_lines.items():
        logger.info("  power line %d for REB ID %d", power_line, rebid)

    for rebid, power_line in power_lines.items():
        reb_power_on(ccs_sub, rebid, power_line, ccd_type)

    logger.info("Stop time: %f", time.time())
