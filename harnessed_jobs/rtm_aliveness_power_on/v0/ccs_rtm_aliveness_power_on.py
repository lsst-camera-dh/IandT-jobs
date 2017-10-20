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

def set_monitoring_interval(ts8, period_ms):
    "Set the CCS ts8 monitoring interval."
    command = "change monitor-update taskPeriodMillis %i" % period_ms
    ts8.synchCommand(10, command)
    command = "change monitor-publish taskPeriodMillis %i" % period_ms
    ts8.synchCommand(10, command)

def reb_power_on(ccs_sub, rebid, power_line, ccd_type):
    logger = ccs_sub.rebps.logger

    reb_current_limits = RebCurrentLimits(ccs_sub.rebps, ccs_sub.ts8)

    rebname = 'REB%d' % rebid
    logger.info("*****************************************************")
    logger.info("Starting power-on procedure for %s (power line %s)",
                rebname, power_line)
    logger.info("*****************************************************")

    # Power on the REB using the power-up sequence.
    ccs_sub.rebps.synchCommand(10, 'sequencePower', power_line, True)

    # Check that the power-supply currents are within the limits
    # for each channel.
    reb_current_limits.check_rebps_limits(rebid)

    # Wait 15 seconds for the FPGA to boot, then check currents again.
    time.sleep(15)
    reb_current_limits.check_rebps_limits(rebid)

    # TODO: Verify data link integrity (LCA-10064-A, p.17, step 5)

    # TODO: Read and record REB 1-wire global unique ID (GUID),
    # then verify it is in the correct slot with power and data
    # cables correctly configured (LCA-10064-A, p.17, step 6)

    # TODO: Read and record the firmware version ID, then verify it is
    # the correct version (LCA-10064-A, p.17, step 7)

    # The reb_info namedtuple contains the info for the REB in question.
    # That information can be used in the step 6 & 7 tests.
    reb_info = get_REB_info(ccs_sub.ts8, rebid)

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
        logger.info("------ %s power-on complete ------\n", rebname)
    except java.lang.Exception as eobj:
        logger.info(eobj.message)
        raise eobj
    finally:
        set_monitoring_interval(ccs_sub.ts8, 10000)

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

    # Set publishing interval to 0.1s for trending plots.
    set_monitoring_interval(ccs_sub.ts8, 100)
    time.sleep(3)

    for rebid, power_line in power_lines.items():
        reb_power_on(ccs_sub, rebid, power_line, ccd_type)

    logger.info("Stop time: %f", time.time())
