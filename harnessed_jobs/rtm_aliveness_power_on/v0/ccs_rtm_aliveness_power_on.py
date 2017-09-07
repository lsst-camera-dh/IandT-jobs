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

CCS.setThrowExceptions(True)

logging.basicConfig(format="%(message)s",
                    level=logging.INFO,
                    stream=sys.stdout)
logger = logging.getLogger()

ChannelInfo = namedtuple('ChannelInfo', ['reb_ps_channel', 'ts8_mon_chan',
                                         'low_lim', 'high_lim', 'chkreb'])

def set_monitoring_interval(ts8, period_ms):
    "Set the CCS ts8 monitoring interval."
    command = "change monitor-update taskPeriodMillis %i" % period_ms
    ts8.synchCommand(10, command)
    command = "change monitor-publish taskPeriodMillis %i" % period_ms
    ts8.synchCommand(10, command)

def power_off_rebs(rebps, lines=(0, 1, 2)):
    "Power-off the requested REBs via the specified power-lines."
    for power_line in lines:
        command = "setNamedPowerOn %d master False" % power_line
        rebps.synchCommand(10, command)

def map_power_lines_to_rebs(ccs_sub, ntries=20, wait_between_tries=10,
                            num_lines=3):
    """
    Map power lines to REBs by powering on one at a time for each REB
    and trying to read the 1-wire ID register.  This function will
    leave the REBs in a powered-off state.
    """
    rebids = ccs_sub.ts8.synchCommand(10, "getREBIds").getResult()
    rebnames = ccs_sub.ts8.synchCommand(10, "getREBDeviceNames").getResult()

    # Ensure that all of the power-lines to the REBs are off to start.
    power_off_rebs(ccs_sub.rebps)

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
            time.sleep(wait_between_tries)
            for i in range(ntries):
                logger.info("%s, try %i", rebname, i)
                try:
                    ccs_sub.ts8.synchCommand(10, 'readRegister %s 1' % rebname)
                    power_line = line
                    logger.info("%s: %i", rebname, power_line)
                    break
                except java.lang.Exception:
                    time.sleep(wait_between_tries)
            power_off_rebs(ccs_sub.rebps, lines=(line,))
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
    command = "readChannelValue %s" % reb_channel_name
    cur_ps = ccs_sub.rebps.synchCommand(10, command).getResult()
    logger.info("REB PS: %s = %s", reb_channel_name, cur_ps)

    ts8_channel_name = 'R00.Reb%d.%s' % (rebid, ts8_mon_chan)
    command = "readChannelValue %s" % ts8_channel_name
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

if __name__ == '__main__':
    # @todo: Read channels to test and their limits from a configuration file.
    channel \
        = dict(digital=ChannelInfo('digital.IaftLDO', 'DigI', 6., 800., False),
               analog=ChannelInfo('analog.IaftLDO', 'AnaI', 6., 610., False),
               clockhi=ChannelInfo('clockhi.IaftLDO', 'ClkHI', 6., 300., True),
               clocklo=ChannelInfo('clocklo.IaftLDO', 'ClkLI', 6., 300., True),
               od=ChannelInfo('OD.IaftLDO', 'ODI', 6., 190., True))

    logger.info("start tstamp: %f", time.time())

    if subsystems is None:
        subsystems = dict(ts8='ts8', rebps='ccs-rebps')

    ccs_sub = CcsSubsystems(subsystems=subsystems, logger=logger)

    logger.info("Mapping power supply lines to REBs...")
    power_lines = map_power_lines_to_rebs(ccs_sub)

    logger.info("will attempt to power on and check currents for")
    for rebid, power_line in power_lines.items():
        logger.info("  power line %d for REB ID %d", power_line, rebid)

    # Set publishing interval to 0.1s for trending plots.
    set_monitoring_interval(ccs_sub.ts8, 100)
    time.sleep(3)

    # This is the order to power on the various channels.
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

            # Allow current to settle after powering on.
            time.sleep(10)

            # Check the channel values:
            try:
                if name in channel:
                    check_values(ccs_sub, rebid, name, *channel[name])
            except java.lang.Exception as eobj:
                logger.info("%s: current check failed for %s",
                            rebname, name)
                logger.info(eobj.message)
                power_on_ok = False
                break

            time.sleep(2)

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
            command = "powerOn %d" % rebid
            outfile = '%s_REB%i_%s_powerOn_aliveness_test_output.txt' \
                      % (UNITID, rebid, RUNNUM)
            outfile = '/'.join((tsCWD, outfile))
            logger.info('writing powerOn output to %s', outfile)
            with open(outfile, 'w') as output:
                output.write(ccs_sub.ts8.synchCommand(900, command).getResult())
            os.chmod(outfile, 0664)
            logger.info("------ %s power-on complete ------\n", rebname)
        except java.lang.Exception as eobj:
            logger.info(eobj.message)
            set_monitoring_interval(ccs_sub.ts8, 10000)
            raise eobj

    set_monitoring_interval(ccs_sub.ts8, 10000)

    if power_on_ok:
        logger.info("DONE with successful powering of REBs.")
    else:
        logger.info("FAILED to turn on all requested REBs")

    logger.info("stop tstamp: %f", time.time())
