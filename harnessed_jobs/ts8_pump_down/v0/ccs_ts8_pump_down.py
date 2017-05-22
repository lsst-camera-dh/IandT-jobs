"""
Jython script for pump down of TS8.

This is based on harnessed-jobs/T08/ts8_pump.
"""
import time
from ccs_scripting_tools import CcsSubsystems, CCS
from eo_acquisition import hit_target_pressure, logger

CCS.setThrowExceptions(True)

if subsystems is None:
    subsystems = dict(vac='ts/VacuumGauge', pdu='ts/PDU')

ccs_sub = CcsSubsystems(subsystems, logger=logger)

# Target pressure for turbo pump.
target = 0.1
hit_target_pressure(ccs_sub.vac, target, wait=5, tmax=7200, logger=logger)
logger.info("Turning on power to the turbo pump.")

# pump_outlet is set in the CcsSetup class to os.environ['CCS_PUMP_OUTLET']
ccs_sub.pdu(120, "setOutletState %s True" % pump_outlet)
