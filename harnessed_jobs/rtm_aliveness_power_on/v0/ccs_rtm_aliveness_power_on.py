"""
Power-on aliveness tests script, based on Homer's
harnessed-jobs/T08/rebalive_power/ccseorebalive_power.py script.

"""
import sys
import time
from collections import namedtuple
import logging
import subprocess
import java.lang
from org.lsst.ccs.scripting import CCS

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s",
#                    level=logging.DEBUG,
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

class CcsSubsystems(object):
    def __init__(self, subsystems=None):
        if subsystems is None:
            subsystems = dict(ts8='ts8', rebps='ccs-rebps')
        for key, value in subsystems.items():
            self.__dict__[key] = CCS.attachSubsystem(value)

ChannelInfo = namedtuple('ChannelInfo', ['reb_ps_channel', 'ts8_mon_chan',
                                         'low_lim', 'high_lim', 'chkreb'])

# @todo: Read channels to test and their limits from a configuration file.
channel = dict(digital=ChannelInfo('digital.IaftLDO', 'DigI', 6., 800., False),
               analog=ChannelInfo('analog.IaftLDO', 'AnaI', 6., 610., False),
               clockhi=ChannelInfo('clockhi.IaftLDO', 'ClkHI', 6., 300., True),
               clocklo=ChannelInfo('clocklo.IaftLDO', 'ClkLI', 6., 300., True),
               od=ChannelInfo('OD.IaftLDO', 'ODI', 6., 190., True))

def power_off_rebs(lines=(0, 1, 2)):
    # Power-off the requested REBs via the specified power-lines.
    for power_line in lines:
        command = "setNamedPowerOn %d master False" % power_line
        logger.debug(command)
        ccs_sub.rebps.synchCommand(10, command)

def map_power_lines_to_rebs(ccs_sub, ntries=10, wait_between_tries=3,
                            num_lines=3):
    """
    Map power lines to REBs by powering on one at a time for each REB
    and trying to read the 1-wire ID register.  This function will
    leave the REBs in a powered-off state.
    """
    rebids = ccs_sub.ts8.synchCommand(10, "getREBIds").getResult()
    rebnames = ccs_sub.ts8.synchCommand(10, "getREBDeviceNames").getResult()

    # Ensure that all of the power-lines to the REBs are off to start.
    power_off_rebs()

    # Loop over each REB to find the line it uses.
    power_lines = {}
    for rebid, rebname in zip(rebids, rebnames):
        line = 0
        power_line = None
        while power_line is None and line < num_lines:
            if line in power_lines.values():
                line += 1
                continue
            for name in 'master digital analog'.split():
                ccs_sub.rebps.synchCommand(10, 'setNamedPowerOn %d %s True'
                                           % (line, name))
                time.sleep(0.5)
            for i in range(ntries):
                logger.debug("%s, try %i", rebname, i)
                try:
                    ccs_sub.ts8.synchCommand(10, 'readRegister %s 1' % rebname)
                    power_line = line
                    logger.debug("%s: %i", rebname, power_line)
                    break
                except java.lang.Exception:
                    time.sleep(wait_between_tries)
            power_off_rebs(lines=(line,))
            line += 1
        if power_line is None:
            raise java.lang.Exception("Could not read register of %s."
                                      % rebname)
        power_lines[rebid] = power_line
    return power_lines

def check_values(ccs_sub, rebid, name, rebps_channel, ts8_mon_chan, low_lim,
                 high_lim, chkreb, logger=logger):
    """
    Check that power supply current (or voltage) levels are within the
    specified range.
    """
    reb_channel_name = 'REB%d.%s' % (rebid, rebps_channel)
    command = "getChannelValue %s" % reb_channel_name
    logger.debug(command)
    cur_ps = ccs_sub.rebps.synchCommand(10, command).getResult()
    logger.info("REB PS: %s = %s", reb_channel_name, cur_ps)

    ts8_channel_name ='R00.Reb%d.%s' % (rebid, ts8_mon_chan)
    command = "getChannelValue %s" % ts8_channel_name
    logger.debug(command)
    cur_reb = ccs_sub.ts8.synchCommand(10, command).getResult()
    logger.info("TS8 Monitor: %s = %s", ts8_channel_name, cur_reb)

    if cur_ps < low_lim or cur_ps > high_lim:
        ccs_sub.rebps.synchCommand(10, "setNamedPowerOn %d %s False"
                                   % (rebid, name))
        stat = "%s: %s with value %f mA not within specified range %f mA to %f mA.  Power to this channel has been shut off." % (rebname, reb_channel_name, cur_ps, low_lim, high_lim)
        raise java.lang.Exception(stat)

    if abs(cur_ps) > 0.0 and chkreb:
        if abs(cur_reb - cur_ps)/cur_ps > 0.10 and abs(cur_reb) > 0.5:
            logger.warning("WARNING: %s value differs by >10%% from %s value.",
                           reb_channel_name, ts8_channel_name)
    logger.info("")

logger.info("start tstamp: %f", time.time())

ccs_sub = CcsSubsystems()

logger.info("Mapping power supply lines to REBs...")
power_lines = map_power_lines_to_rebs(ccs_sub)

logger.info("will attempt to power on and check currents for")
for rebid, power_line in power_lines.items():
    logger.info("  power line %d for REB ID %d", power_line, rebid)

logger.info("Setting tick and monitoring period to 0.1s for trending plots.")
ccs_sub.ts8.synchCommand(10, "change monitor-update taskPeriodMillis 100")

time.sleep(3)

# This is the order to power on the various named REB lines.
named_lines = ('master', 'digital', 'analog', 'clockhi', 'clocklo',
               'heater', 'od')

power_on_ok = True
for rebid, power_line in power_lines.items():
    rebname = 'REB%d' % rebid
    logger.info("*****************************************************")
    logger.info("Starting power-on procedure for %s (power line %s)",
                rebname, power_line)
    logger.info("*****************************************************")

    for name in named_lines:
        try:
            logger.info("%s: turning on %s power at %s", rebname,
                        name, time.ctime().split()[3])
            ccs_sub.rebps.synchCommand(10, "setNamedPowerOn %d %s True"
                                       % (power_line, name))
        except java.lang.Exception as eobj:
            logger.info("%s: failed to turn on current %s!", rebname, name)
            raise eobj

        time.sleep(10)
        # Checking the channel values here...
        try:
            if name in channel:
                check_values(ccs_sub, rebid, name, *channel[name])
        except java.lang.Exception as eobj:
            logger.info("%s: current check failed for %s", rebname, name)
            logger.info(eobj.message)
            power_on_ok = False
            break

        time.sleep(2)

    logger.info("Proceed to turn on REB clock and rail voltages")
    # load default configuration
    # @todo: Make sure etc folder has correct properities files for
    # these configurations.
#    ccs_sub.ts8.synchCommand(10, "loadCategories Rafts:itl")
#    ccs_sub.ts8.synchCommand(10, "loadCategories RaftsLimits:itl")
#    logger.info("loaded configurations: Rafts:itl")
    try:
# @todo: fix this
#        command = "powerOn %d" % rebid
#        logger.info("running %s", command)
#        result = ccs_sub.ts8.synchCommand(300, command).getResult()
#        logger.info(str(result))
        logger.info("------ %s Complete ------\n", rebname)
    except java.lang.Exception as eobj:
        logger.info(eobj.message)
        raise eobj
    finally:
        logger.info("Re-setting tick and monitoring period to 10s.")
        ccs_sub.ts8.synchCommand(10, "change monitor-update taskPeriodMillis 10000")

if power_on_ok:
    logger.info("DONE with successful powering of REBs.")
else:
    logger.info("FAILED to turn on all requested REBs")

logger.info("stop tstamp: %f" % time.time())
