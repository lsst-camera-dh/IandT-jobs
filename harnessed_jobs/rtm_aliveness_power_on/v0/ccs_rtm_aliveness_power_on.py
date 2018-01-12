"""
Power-on aliveness tests script.  See LCA-10064 section 10.4.2.2.
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

def reb_power_on(ccs_sub, rebid, power_line, ccd_type, raise_exception=True):
    """
    REB power-on script.  This implements steps in LCA-10064
    section 10.4.2.2.

    Parameters
    ----------
    ccs_sub : CcsSubsystems object
        Container for ts8 and rebps subsystems.
    rebid : int
        REB id number. Usually 0, 1, or 2.
    power_line : int
        REB power-supply line, 0, 1, or 2.
    ccd_type : str
        CCD vendor for loading configurations. Valid values are 'ITL', 'E2V'.
    raise_exception : bool, optional
        Flag to raise exceptions.  Default: True
    """
    logger = ccs_sub.rebps.logger

    reb_current_limits = RebCurrentLimits(ccs_sub.rebps, ccs_sub.ts8)

    reb_slot = 'REB%d' % rebid
    logger.info("*****************************************************")
    logger.info("Starting power-on procedure for %s (power line %s)",
                reb_slot, power_line)
    logger.info("*****************************************************")

    reb_device \
        = list(ccs_sub.ts8.synchCommand(10, 'getREBDevices').getResult())[rebid]

    # Power on the REB using the power-up sequence. (10.4.2.2, step 2)
    ccs_sub.rebps.synchCommand(10, 'sequencePower', power_line, True)

    time.sleep(1)
    # Check that the power-supply currents are within the limits
    # for each channel. (10.4.2.2, step 3)
    reb_current_limits.check_rebps_limits(rebid, enforce_lower_limits=False,
                                          raise_exception=raise_exception)

    # Wait 30 seconds for the FPGA to boot, then check currents again.
    # (10.4.2.2, step 4)
    time.sleep(30)
    reb_current_limits.check_rebps_limits(rebid,
                                          raise_exception=raise_exception)

    # Verify the data link by reading a register.  (10.4.2.2, step 5)
    ccs_sub.ts8.synchCommand(10, 'readRegister', reb_device, 1)

    # The reb_info namedtuple contains the info for the REB in question.
    # That information can be used in the step 6 & 7 tests.
    reb_info = get_REB_info(ccs_sub.ts8, 220 + rebid)

    # Compare the REB hardware serial number to the value in the
    # eTraveler tables for this REB in this raft.  (10.4.2.2, step 6)
    if reb_info.serialNumber != reb_eT_info[reb_slot].manufacturer_sn:
        raise java.lang.Exception("REB manufacturer serial number mismatch: %s, %s"
                                  % (reb_info.serialNumber,
                                     reb_eT_info[reb_slot].manufacturer_sn))

    # TODO: Read and record the firmware version ID, then verify it is
    # the correct version (LCA-10064-A, p.17, step 7).  Currently,
    # there is no reliable way of getting the intended firmware version
    # from the eTraveler, so we just print it to the screen.
    # (10.4.2.2, step 7)
    logger.info("%s firmware version from CCS: %s (0x%x)", reb_slot,
                reb_info.hwVersion, reb_info.hwVersion)

    # Check that REB P/S currents match the REB currents from ts8
    # within the comparative limits. (10.4.2.2, step 8)
    reb_current_limits.check_comparative_ranges(rebid,
                                                raise_exception=raise_exception)

    logger.info("Turn on REB clock and rail voltages.")

    # Load configurations
    ccs_sub.ts8.synchCommand(10, "loadCategories Rafts")
    ccs_sub.ts8.synchCommand(10, "loadCategories RaftsLimits")

    # Run the powerOn CCS command (10.4.2.2, steps 11-13)
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
        try:
            reb_power_on(ccs_sub, rebid, power_line, ccd_type)
        except (java.lang.Exception, StandardError) as eobj:
            ccs_sub.rebps.synchCommand(10, 'sequencePower', rebid, False)
            raise

    logger.info("Stop time: %f", time.time())
