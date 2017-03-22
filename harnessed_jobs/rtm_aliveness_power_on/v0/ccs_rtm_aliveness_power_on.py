"""
Power-on aliveness tests script, based on Homer's
harnessed-jobs/T08/rebalive_power/ccseorebalive_power.py script.

"""
import sys
import time
import logging
import subprocess
import java.lang
from org.lsst.ccs.scripting import CCS

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s", level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger()

# @todo: avoid global variables in this function
def check_currents(rebid, pwr_chan, reb_chan, low_lim, high_lim, chkreb,
                   logger=logger):
    """
    Check that PS current levels are within specified range.
    """
    reb_channel_name = "REB%d.%s.IaftLDO" % (rebid, pwr_chan)
    command = "getChannelValue %s" % reb_channel_name
    logger.debug(command)
    cur_ps = pwrsub.synchCommand(10, command).getResult()
    logger.info("REB PS: %s = %s", reb_channel_name, cur_ps)

    ts8_channel_name = "R00.Reb%d.%s" % (rebid, reb_chan)
    command = "getChannelValue %s" % ts8_channel_name
    logger.debug(command)
    cur_reb = ts8sub.synchCommand(10, command).getResult()
    logger.info("TS8 Monitor: %s = %s", ts8_channel_name, cur_reb)

    if cur_ps < low_lim or cur_ps> high_lim:
        pwrsub.synchCommand(10, "setNamedPowerOn %d %s False" % (rebid, pwr))
        stat = "%s: %s with value %f mA not within specified range %f mA to %f mA.  Power to this channel has been shut off." % (rebname, reb_channel_name, cur_ps, low_lim, high_lim)
        raise java.lang.Exception(stat)

    if abs(cur_ps) > 0.0 and chkreb:
        if abs(cur_reb - cur_ps)/cur_ps > 0.10 and abs(cur_reb) > 0.5:
            logger.warning("%s value differs by >10%% from %s value.",
                           reb_channel_name, ts8_channel_name)
    logger.info("")
    return

try:
    cdir = tsCWD
    unit = CCDID
except java.lang.Exception as eobj:
    logger.debug(str(eobj))
    logger.info("Running in standalone mode, outside of JH/eT.")

logger.info("start tstamp: %f", time.time())

ts8sub = CCS.attachSubsystem("ts8")
pwrsub = CCS.attachSubsystem("ccs-rebps")
pwrmainsub = CCS.attachSubsystem("ccs-rebps/MainCtrl")

result = pwrsub.synchCommand(10, "getChannelNames")
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
    rebids = ts8sub.synchCommand(10, "getREBIds").getResult()
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
#ts8sub.synchCommand(10, "change tickMillis 100");
#ts8sub.synchCommand(10, "setTickMillis 100")

power_on_successful = True
for ids in idmap:
    pwrid = int(ids.split(":")[0])
    rebid = int(ids.split(":")[1])

    i = pwrid
    rebname = 'REB%d' % i
    logger.info("*****************************************************")
    logger.info("Starting power-on procedure for %s (power line %s)",
                rebname, pwrid)
    logger.info("*****************************************************")

    # Verify that all power is off to start.
    pwrsub.synchCommand(20, "setNamedPowerOn %d master False" % i);

    time.sleep(3.0)

    # Attempt to apply the REB power line by line:
    powers = ['master', 'digital', 'analog', 'clockhi', 'clocklo',
              'heater', 'od']
    chkreb = True #False

    for pwr in powers:
        if 'clockhi' in pwr:
            chkreb = True
# @todo: determine where reboot should really occur
#            logger.info("Rebooting the RCE after a 5s wait")
#            time.sleep(5.0)
#            sout = subprocess.check_output("$HOME/rebootrce.sh", shell=True)
#            logger.info(sout)
#            time.sleep(2.0)
        try:
            logger.info("%s: turning on %s power at %s", rebname,
                        pwr, time.ctime().split()[3])
            pwrsub.synchCommand(10,"setNamedPowerOn %d %s True" % (i, pwr))
        except java.lang.Exception as eobj:
            logger.info("%s: failed to turn on current %s!", rebname, pwr)
            raise eobj

        time.sleep(2)
        try:
            if 'digital' in pwr:
                check_currents(i, "digital", "DigI", 6., 800., chkreb)
            if 'analog' in pwr:
                check_currents(i, "analog", "AnaI", 6., 610., chkreb)
            if 'od' in pwr:
                check_currents(i, "OD", "ODI", 6., 190., chkreb)
            if 'clockhi' in pwr:
                check_currents(i, "clockhi", "ClkHI", 6.0, 300., chkreb)
            if 'clocklo' in pwr:
                check_currents(i, "clocklo", "ClkLI", 6., 300., chkreb)
# @todo: check heater currents?
        except java.lang.Exception as eobj:
            logger.info("%s: current check failed for %s", rebname, pwr)
            logger.info(eobj.message)
            power_on_successful = False
            break

        time.sleep(2)

    logger.info("Proceed to turn on REB clock and rail voltages")
#    # load default configuration
# @todo: fix this
#    ts8sub.synchCommand(10, "loadCategories Rafts:itl")
#    ts8sub.synchCommand(10, "loadCategories RaftsLimits:itl")
#    logger.info("loaded configurations: Rafts:itl")
    try:
# @todo: fix this
#        logger.info("running powerOn %d command", rebid)
#        result = ts8sub.synchCommand(300, "powerOn %d" % rebid).getResult()
#        logger.info(str(result))
        logger.info("------ %s Complete ------\n", rebname)
    except java.lang.Exception as eobj:
        logger.info(eobj.message)
#        print "setting tick and monitoring period to 10s"
#        ts8sub.synchCommand(10, "change tickMillis 10000");
#        raise eobj

#print "setting tick and monitoring period to 10s"
#ts8sub.synchCommand(10, "change tickMillis 10000");

if power_on_successful:
    logger.info("DONE with successful powering of REBs.")
else:
    logger.info("FAILED to turn on all requested REBs")

logger.info("stop tstamp: %f" % time.time())
