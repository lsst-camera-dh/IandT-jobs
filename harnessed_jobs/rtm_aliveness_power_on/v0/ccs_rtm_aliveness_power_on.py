###############################################################################
# REB-PS safe power on
#
#
# author: homer    10/2016
#
###############################################################################

from org.lsst.ccs.scripting import CCS
from java.lang import Exception
import sys
import time
import subprocess


CCS.setThrowExceptions(True);

def check_currents(rebid, pwr_chan, reb_chan, low_lim, high_lim, chkreb):
    """
    Check that PS current levels are within acceptable range.
    """
    command = "getChannelValue REB%d.%s.IaftLDO" % (rebid, pwr_chan)
    print command
    cur_ps = pwrsub.synchCommand(10, command).getResult()
    print "Retrieved REB PS current %s: %s " % (pwr_chan, cur_ps)

    command = "getChannelValue R00.Reb%d.%s" % (rebid, reb_chan)
    print command
    cur_reb = ts8sub.synchCommand(10, command).getResult()
    print "Retrieved REB current %s: %s " % (reb_chan, cur_reb)

    print "verifying that the current is with limits"
    if chkreb:
#        stat = "%s: - checking %10.10s : OK - PS value is %8.3f mAmps, REB value is %8.3f mAmps" % (rebname, pwr_chan, cur_ps, cur_reb)
        stat = "%s: - checking %s : OK - PS value is %s mAmps, REB value is %s mAmps\n" % (rebname, pwr_chan, cur_ps, cur_reb)
    else:
#        stat = "%s: - checking %10.10s : OK - PS value is %8.3f mAmps, REB not yet ON" % (rebname, pwr_chan, cur_ps)
        stat = "%s: - checking %s : OK - PS value is %s mAmps, REB not yet ON" % (rebname, pwr_chan, cur_ps)

        print " ... stat = ", stat

    if cur_ps < low_lim or cur_ps> high_lim:
        pwrsub.synchCommand(10, "setNamedPowerOn %d %s False" % (rebid,pwr))
        stat = "%s: Current %s with value %f mA NOT in range %f mA to %f mA. POWER TO THIS CHANNEL HAS BEEN SHUT OFF!" % (rebname, pwr_chan, cur_ps, low_lim, high_lim)
        raise Exception(stat)

    if abs(cur_ps) > 0.0 and chkreb:
        if abs(cur_reb-cur_ps)/cur_ps > 0.10 and abs(cur_reb) > 0.5:
            stat = "%s: Current %s with value %f differs by > 10%% to current from reb channel %s with value %f!" % (rebname, pwr_chan, cur_ps, reb_chan, cur_reb)
#            pwrsub.synchCommand(10,"setNamedPowerOn %d %s False" % (rebid,pwr))
#            stat = "%s: Current %s with value %f differs by > 20%% to current from reb channel %s with value %f. POWER TO THIS CHANNEL HAS BEEN SHUT OFF!" % (rebname,pwr_chan,cur_ps,reb_chan,cur_reb)
#            raise Exception(stat)

    print stat + "\n"
    print "*************\n"
    return

class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
#        self.log = open("%s/rebalive_results.txt" % tsCWD, "a")
        self.log = sys.stdout

    def write(self, message):
        self.terminal.write(message+"\n")
        self.log.write(message + "\n")

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass

dorun = True

# The following will cause an exception if not run as part of a harnessed job because
# tsCWD and CCDID will not be defined in that case
try:
    cdir = tsCWD
    unit = CCDID
#    sys.stdout = Logger()
    print "Running as a job harness. Results are being recorded in rebalive_results.txt"
except Exception as eobj:
    print str(eobj)
    print "Running standalone. Statements will be sent to standard output."

print "start tstamp: %f" % time.time()

if not dorun:
    print "setup for repair ... not running"
else:
    # attach CCS subsystem Devices for scripting
    ts8sub = CCS.attachSubsystem("ts8")
    pwrsub = CCS.attachSubsystem("ccs-rebps")
    pwrmainsub = CCS.attachSubsystem("ccs-rebps/MainCtrl")

    status_value = True

    result = pwrsub.synchCommand(10, "getChannelNames")
    channames = result.getResult()

#    print channames
    rebids = ts8sub.synchCommand(10, "getREBIds").getResult()

    idmap = []

    print "length = %d" % len(sys.argv)
    print str(sys.argv)

    for arg in sys.argv :
        if ":" in arg :
            idmap.append(arg)

    # check for one by one connectivity jobs
    if "connectivity0" in jobname:
        idmap.append("0:0")
    if "connectivity1" in jobname:
        idmap.append("1:1")
    if "connectivity2" in jobname:
        idmap.append("2:2")

    # if nothing specified ... do it all
    if len(idmap) == 0:
        for rebid in rebids:
            print "rebid = %s" % rebid
            idmap.append("%d:%d" % (int(rebid), int(rebid)))

    print "Will attempt to power on:"
    for ids in idmap:
        pwrid = int(ids.split(":")[0])
        rebid = int(ids.split(":")[1])
        print "power line %d for REB ID %d" % (pwrid,rebid)


#    print "setting tick and monitoring period to 0.1s"
#    ts8sub.synchCommand(10, "change tickMillis 100");
#    ts8sub.synchCommand(10, "setTickMillis 100")

    for ids in idmap[:1]:
        pwrid = int(ids.split(":")[0])
        rebid = int(ids.split(":")[1])

        if status_value:
            i = pwrid
            rebname = 'REB%d' % i
            print "****************************************************"
            print " Starting power ON procedure for REB power line %s and REB %s\n" % (pwrid,rebname)
            print "****************************************************"


            # verify that all power is OFF
            try:
#                result = pwrsub.synchCommand(10, "setNamedPowerOn", i, "master", False);
                result = pwrsub.synchCommand(20, "setNamedPowerOn %d master False" % i);
            except Exception as e:
                print "%s: FAILED TO TURN POWER OFF! %s" % (rebname, e)
                raise Exception

            time.sleep(3.0)

            pwron = ""
            # attempt to apply the REB power -- line by line
            powers = ['master', 'digital', 'analog', 'clockhi', 'clocklo', 'heater', 'od']
            chkreb = True #False

            for pwr in powers:
                pwron = pwron + pwr + " "
                if 'clockhi' in pwr:
                    chkreb = True
#                    print "Rebooting the RCE after a 5s wait"
#                    time.sleep(5.0)
#                    sout = subprocess.check_output("$HOME/rebootrce.sh", shell=True)
#                    print sout
#                    time.sleep(2.0)
                    continue
                try:
                    print "%s: turning on %s power at %s" % (rebname,pwr,time.ctime().split()[3])
                    pwrsub.synchCommand(10,"setNamedPowerOn %d %s True" % (i,pwr));
                except:
                    print "%s: failed to turn on current %s!" % (rebname,pwr)
                    throw

                time.sleep(2.0)
                try:
                    if 'digital' in pwron:
                        check_currents(i, "digital", "DigI", 6., 800., chkreb)
                    if 'analog' in pwron:
                        check_currents(i, "analog", "AnaI", 6., 610., chkreb)
                    if 'od' in pwron:
                        check_currents(i, "OD", "ODI", 6., 190., chkreb)
                    if 'clockhi' in pwron:
                        check_currents(i, "clockhi", "ClkHI", 6.0, 300., chkreb)
                    if 'clocklo' in pwron:
                        check_currents(i, "clocklo", "ClkLI", 6., 300., chkreb)
##                   check_currents(i,"heater","???",0.100,0.300,chkreb)
                except Exception as e:
                    print "%s: CURRENT CHECK FAILED! %s" % (rebname, e)
                    status_value = False
                    raise Exception

                time.sleep(2)

            if status_value:
                print "PROCEED TO TURN ON REB CLOCK AND RAIL VOLTAGES"
                # load default configuration
                ts8sub.synchCommand(10, "loadCategories Rafts:itl")
                ts8sub.synchCommand(10, "loadCategories RaftsLimits:itl")
                print "loaded configurations: Rafts:itl"
                try:
                    print "running powerOn %d command" % rebid
                    stat = ts8sub.synchCommand(300, "powerOn %d" % rebid).getResult()
                    print stat
                    print "------ %s Complete ------\n" % rebname
                except Exception as e:
#                    print e
#                    print "setting tick and monitoring period to 10s"
#                    ts8sub.synchCommand(10, "change tickMillis 10000");
                    raise e

#    print "setting tick and monitoring period to 10s"
#    ts8sub.synchCommand(10, "change tickMillis 10000");

    if status_value:
        print "DONE with successful powering of"
        print rebids
    else:
        print "FAILED to turn on all requested rebs"

print "stop tstamp: %f" % time.time()
