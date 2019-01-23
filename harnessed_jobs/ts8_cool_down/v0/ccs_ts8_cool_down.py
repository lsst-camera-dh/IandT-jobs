"""
Jython script for cool down of TS8.

This is based on harnessed-jobs/T08/ts8_cool_down.
"""
import time
from ccs_scripting_tools import CcsSubsystems, CCS
from eo_acquisition import hit_target_pressure, logger

CCS.setThrowExceptions(True)

if subsystems is None:
    subsystems = dict(ts='ts', vac='ts/VacuumGauge', pdu='ts/PDU',
                      cryo='ts/Cryo')

ccs_sub = CcsSubsystems(subsystems, logger=logger)

# Wait until targer pressure is attained before turning on the cryocooler.
target = 1e-3
hit_target_pressure(ccs_sub.vac, target, wait=5, tmax = 7200, logger=logger)

logger.info("Turning on power to the Polycold cryocooler.")
# cryo_outlet is set in the CcsSetup class to os.environ['CCS_CRYO_OUTLET'].
ccs_sub.pdu.synchCommand(120, "setOutletState %s True" % cryo_outlet)

# Maximum elasped time for ready state.
tmax = 18000
# Wait time between test stand readiness polls.
twait = 5
# Move the teststand to the ready state.
ready_state = ccs_sub.ts.asynchCommand('setTSReady')
ts_state = 0
while ts_state == 0:
    try:
        ts_state = ccs_sub.ts.synchCommand(10, "isTestStandReady")
        ctemp = ccs_sub.cryo.synchCommand(20, "getTemp B")
        logger.info("time = %s, temp = %f", time.time(), ctemp)
    except StandardError as eobj:
        logger.info("Exception caught while waiting for test stand ready state")
        logger.info(str(eobj))
    if (time.time() - tstart) > tmax:
        raise RuntimeError("Wait time for test stand ready state exceeded.")
    time.sleep(twait)

# Final check of test stand readiness.
reply = ready_state.get()
result = ccs_sub.ts.synchCommand(120, "goTestStand")
