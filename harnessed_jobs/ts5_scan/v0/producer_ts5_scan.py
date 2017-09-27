#!/usr/bin/env python
import subprocess
import os.path
import siteUtils

raft_id = siteUtils.getUnitId()

# Get the working directory of this script because it contains other executables that we'll use
path_to_executables = os.path.dirname(__file__)

commandstr = 'perl ' + path_to_executables + '/slac_ts5_metro_scan.perl'

subprocess.check_call(commandstr, shell=True)

commandstr = 'perl ' + path_to_executables + '/slac_ts5_dlog.perl'

if 1:
    subprocess.check_call(commandstr, shell=True)
else:
    subprocess.check_call('cp /lnfs/lsst/devel/ccs/ts5/LCA-10753_RSA_004_ETU02_170919221019.tnt dont_trust_this_data.txt', shell=True)
