"""
CCS script to dump the sequencer file paths to a json file.
"""
import sys
import json
from org.lsst.ccs.scripting import CCS

fp = CCS.attachSubsystem('focal-plane')

ccs_output = fp.sendSynchCommand('getSequencerPaths')
output = {str(key): str(value) for key, value in ccs_output.items()}

if len(sys.argv) > 1:
    outfile = sys.argv[1]
else:
    outfile = 'sequencer_paths.json'

with open(outfile, 'w') as fd:
    json.dump(output, fd)
