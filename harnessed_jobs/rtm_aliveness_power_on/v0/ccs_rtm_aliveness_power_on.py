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

channels = dict(digital=ChannelInfo('REB%d.digital.IaftLDO', 'R00.Reb%d.DigI',
                                    6., 800., False),
                analog=ChannelInfo('REB%d.analog.IaftLDO', 'R00.Reb%d.AnaI',
                                   6., 610., False),
                clockhi=ChannelInfo('REB%d.clockhi.IaftLDO', 'R00.Reb%d.ClkHI',
                                    6., 300., True),
                clocklo=ChannelInfo('REB%d.clocklo.IaftLDO', 'R00.Reb%d.ClkLI',
                                    6., 300., True),
                od=ChannelInfo('REB%d.OD.IaftLDO', 'R00.Reb%d.ODI',
                               6., 190., True))

def check_values(ccs_sub, rebid, pwr, rebps_channel, ts8_mon_chan, low_lim,
                 high_lim, chkreb, logger=logger):
    """
    Check that power supply current (or voltage) levels are within the
    specified range.
    """
    reb_channel_name = rebps_channel % rebid
    command = "getChannelValue %s" % reb_channel_name
    logger.debug(command)
    cur_ps = ccs_sub.rebps.synchCommand(10, command).getResult()
    logger.info("REB PS: %s = %s", reb_channel_name, cur_ps)

    ts8_channel_name = ts8_mon_chan % rebid
    command = "getChannelValue %s" % ts8_channel_name
    logger.debug(command)
    cur_reb = ccs_sub.ts8.synchCommand(10, command).getResult()
    logger.info("TS8 Monitor: %s = %s", ts8_channel_name, cur_reb)

    if cur_ps < low_lim or cur_ps > high_lim:
        ccs_sub.rebps.synchCommand(10, "setNamedPowerOn %d %s False"
                                   % (rebid, pwr))
        stat = "%s: %s with value %f mA not within specified range %f mA to %f mA.  Power to this channel has been shut off." % (rebname, reb_channel_name, cur_ps, low_lim, high_lim)
        raise java.lang.Exception(stat)

    if abs(cur_ps) > 0.0 and chkreb:
        if abs(cur_reb - cur_ps)/cur_ps > 0.10 and abs(cur_reb) > 0.5:
            logger.warning("WARNING: %s value differs by >10%% from %s value.",
                           reb_channel_name, ts8_channel_name)
    logger.info("")

logger.info("start tstamp: %f", time.time())

ccs_sub = CcsSubsystems()

logger.debug(ccs_sub.rebps.synchCommand(10, "getChannelNames").getResult())

# Map REB IDs and power lines.
rebids = ccs_sub.ts8.synchCommand(10, "getREBIds").getResult()
idmap = []
for item in rebids:
    rebid = int(item)
    # For now, just assume power line = REB ID.
    pwrid = rebid
    idmap.append((pwrid, rebid))

logger.info("Will attempt to power on:")
for pwrid, rebid in idmap:
    logger.info("power line %d for REB ID %d", pwrid, rebid)

logger.info("Setting tick and monitoring period to 0.1s.")
ccs_sub.ts8.synchCommand(10, "change monitor-update taskPeriodMillis 100")
#ccs_sub.rebps.synchCommand(10, "setUpdatePeriod 100")

# Ensure that power is off to all three REBs before proceeding with
# the power-on sequences.
for pwrid, rebid in idmap:
    command = "setNamedPowerOn %d master False" % pwrid
    logger.debug(command)
    ccs_sub.rebps.synchCommand(20, command)
time.sleep(3)

# This is the order to power on the various REB lines.
power_on_list = ['master', 'digital', 'analog',
                 'clockhi', 'clocklo', 'heater', 'od']

power_on_ok = True
for pwrid, rebid in idmap:
    rebname = 'REB%d' % rebid
    logger.info("*****************************************************")
    logger.info("Starting power-on procedure for %s (power line %s)",
                rebname, pwrid)
    logger.info("*****************************************************")

    for pwr in power_on_list:
        if 'clockhi' in pwr:
            pass
#            logger.info("Rebooting the RCE after a 5s wait")
#            time.sleep(5.0)
#            sout = subprocess.check_output("$HOME/rebootrce.sh", shell=True)
#            logger.info(sout)
#            time.sleep(2.0)
        try:
            logger.info("%s: turning on %s power at %s", rebname,
                        pwr, time.ctime().split()[3])
            ccs_sub.rebps.synchCommand(10, "setNamedPowerOn %d %s True"
                                       % (pwrid, pwr))
        except java.lang.Exception as eobj:
            logger.info("%s: failed to turn on current %s!", rebname, pwr)
            raise eobj

        time.sleep(10)
        try:
            if pwr in channels:
                check_values(ccs_sub, rebid, pwr, *channels[pwr])
        except java.lang.Exception as eobj:
            logger.info("%s: current check failed for %s", rebname, pwr)
            logger.info(eobj.message)
            power_on_ok = False
            break

        time.sleep(2)

    logger.info("Proceed to turn on REB clock and rail voltages")
    # load default configuration
    # @todo: Make sure etc folder has correct properities files for
    # these configurations.
    ccs_sub.ts8.synchCommand(10, "loadCategories Rafts:itl")
    ccs_sub.ts8.synchCommand(10, "loadCategories RaftsLimits:itl")
    logger.info("loaded configurations: Rafts:itl")
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
