"""
Jython script to run EO acquisition sequences on the BOT.
"""
import sys
import logging
from org.lsst.ccs.scripting import CCS
from org.lsst.ccs.bus.states import AlertState

sys.path.insert(0, sys.argv[1])
from ccs_scripting_tools import CcsSubsystems

logging.basicConfig(format="%(message)s",
                    level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('ccs_BOT_acq.py')

subsystems = dict(fp = 'focal-plane-sim')
ccs_sub = CcsSubsystems(subsystems, logger=logger)
ccs_sub.write_versions()

CCS.setThrowExceptions(True)

fp = CCS.attachSubsystem('focal-plane-sim')

alerts = ccs_sub.fp.synchCommand('getRaisedAlertSummary')

if alerts.alertState != AlertState.NOMINAL:
    logger.info("WARNING: focal-plane subsystem is in alert state %s",
                alerts.alertState)
    logger.info(alerts)

ccs_sub.fp.synchCommand("clear", 1)
