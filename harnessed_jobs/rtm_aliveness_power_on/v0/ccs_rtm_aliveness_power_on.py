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

logging.basicConfig(format="%(message)s", level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

class CcsSubsystems(object):
    def __init__(self, subsystems=None):
        if subsystems is None:
            subsystems = dict(ts8='ts8', rebps='ccs-rebps')
        for key, value in subsystems.items():
            self.__dict__[key] = CCS.attachSubsystem(value)

ChannelInfo = namedtuple('ChannelInfo', ['pwr_chan', 'reb_chan', 'low_lim',
                                         'high_lim', 'chkreb'])

channels = dict(digital=ChannelInfo('digital', 'DigI', 6., 800., False),
                analog=ChannelInfo('analog', 'AnaI', 6., 610., False),
                clockhi=ChannelInfo('clockhi', 'ClkHI', 6., 300., True),
                clocklo=ChannelInfo('clocklo', 'ClkLI', 6., 300., True),
                od=ChannelInfo('OD', 'ODI', 6., 190., True))

def check_currents(ccs_sub, rebid, pwr_chan, reb_chan, low_lim, high_lim,
                   chkreb, logger=logger):
    """
    Check that PS current levels are within specified range.
    """
    reb_channel_name = "REB%d.%s.IaftLDO" % (rebid, pwr_chan)
    command = "getChannelValue %s" % reb_channel_name
    logger.debug(command)
    cur_ps = ccs_sub.rebps.synchCommand(10, command).getResult()
    logger.info("REB PS: %s = %s", reb_channel_name, cur_ps)

    ts8_channel_name = "R00.Reb%d.%s" % (rebid, reb_chan)
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

try:
    cdir = tsCWD
    unit = CCDID
except java.lang.Exception as eobj:
    logger.debug(str(eobj))
    logger.info("Running in standalone mode, outside of JH/eT.")

ccs_sub = CcsSubsystems()

logger.info("start tstamp: %f", time.time())

result = ccs_sub.rebps.synchCommand(10, "getChannelNames")
channames = result.getResult()
logger.debug(channames)

idmap = []
# Get desired REBs from command line arguments
# @todo: refactor this.
for arg in sys.argv:
    if ":" in arg:
        idmap.append(arg)

if len(idmap) == 0:
    # Loop over all three REBs.
    rebids = ccs_sub.ts8.synchCommand(10, "getREBIds").getResult()
    for rebid in rebids:
        logger.info("rebid = %s" % rebid)
        idmap.append("%d:%d" % (int(rebid), int(rebid)))

print "Will attempt to power on:"
for ids in idmap:
    pwrid = int(ids.split(":")[0])
    rebid = int(ids.split(":")[1])
    logger.info("power line %d for REB ID %d", pwrid, rebid)

# @todo: determine if 0.1 sampling is needed
#print "setting tick and monitoring period to 0.1s"
#ccs_sub.ts8.synchCommand(10, "change tickMillis 100");
#ccs_sub.ts8.synchCommand(10, "setTickMillis 100")

current_check_ok = True
for ids in idmap:
    pwrid = int(ids.split(":")[0])
    rebid = int(ids.split(":")[1])

    rebname = 'REB%d' % rebid
    logger.info("*****************************************************")
    logger.info("Starting power-on procedure for %s (power line %s)",
                rebname, pwrid)
    logger.info("*****************************************************")

    # Verify that all power is off to start.
    # @todo: check whether this should use pwrid or rebid
    ccs_sub.rebps.synchCommand(20, "setNamedPowerOn %d master False" % pwrid);

    time.sleep(3.0)

    # Attempt to apply the REB power line by line:
    powers = ['master', 'digital', 'analog', 'clockhi', 'clocklo',
              'heater', 'od']

    for pwr in powers:
        if 'clockhi' in pwr:
            pass
# @todo: determine where reboot should really occur
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

        time.sleep(2)
        try:
            if pwr in channels:
                check_currents(ccs_sub, rebid, *channels[pwr])
        except java.lang.Exception as eobj:
            logger.info("%s: current check failed for %s", rebname, pwr)
            logger.info(eobj.message)
            current_check_ok = False
            break

        time.sleep(2)

    logger.info("Proceed to turn on REB clock and rail voltages")
#    # load default configuration
# @todo: fix this
#    ccs_sub.ts8.synchCommand(10, "loadCategories Rafts:itl")
#    ccs_sub.ts8.synchCommand(10, "loadCategories RaftsLimits:itl")
#    logger.info("loaded configurations: Rafts:itl")
    try:
# @todo: fix this
#        logger.info("running powerOn %d command", rebid)
#        result = ccs_sub.ts8.synchCommand(300, "powerOn %d" % rebid).getResult()
#        logger.info(str(result))
        logger.info("------ %s Complete ------\n", rebname)
    except java.lang.Exception as eobj:
        logger.info(eobj.message)
#        print "setting tick and monitoring period to 10s"
#        ccs_sub.ts8.synchCommand(10, "change tickMillis 10000");
#        raise eobj

#print "setting tick and monitoring period to 10s"
#ccs_sub.ts8.synchCommand(10, "change tickMillis 10000");

if current_check_ok:
    logger.info("DONE with successful powering of REBs.")
else:
    logger.info("FAILED to turn on all requested REBs")

logger.info("stop tstamp: %f" % time.time())
