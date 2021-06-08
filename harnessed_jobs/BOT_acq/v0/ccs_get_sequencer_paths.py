"""
CCS script to dump the sequencer file paths to a json file.
"""
import os
import sys
import json
from org.lsst.ccs.scripting import CCS

ccs_subsystem = os.environ.get('LCATR_CCS_SUBSYSTEM', 'focal-plane')
print('Using CCS subsystem:', ccs_subsystem)

fp = CCS.attachSubsystem(ccs_subsystem)

ccs_output = fp.sendSynchCommand('getSequencerPaths')
output = {str(key): str(value) for key, value in ccs_output.items()}

if len(sys.argv) > 1:
    outfile = sys.argv[1]
else:
    outfile = 'sequencer_paths.json'

with open(outfile, 'w') as fd:
    json.dump(output, fd)
