#!/usr/bin/env python
# from ccsTools import ccsProducer
import subprocess
import siteutils

raft_id = siteUtils.getUnitId()

# Set up the command for the subprocess call
# N.B. The path to the scripts needs to be defined relative to the installation directory

commandstr = 'perl /u/gl/digel/lsst/IandT-jobs/harnessed_jobs/ts5_scan/v0/slac_ts5_dlog.perl --input_file=' +
              raft_id + '_scan_plan.tnt'

# Below the Perl script executes the scan plan that has already been
# written.  The paths to the Perl script and the scan plan need to
# be hardwired.

subprocess.check_call(commandstr, shell=True)
