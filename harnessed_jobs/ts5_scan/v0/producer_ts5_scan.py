#!/usr/bin/env python
# from ccsTools import ccsProducer
import subprocess
import siteUtils

raft_id = siteUtils.getUnitId()

# Set up the command for the subprocess call to generate the scan plan file
# N.B. The path to the scripts needs to be defined relative to the installation directory
commandstr = 'perl slac_ts5_metro_scan.perl ' +
             '--sensor_sample_spacing=0.5 ' +
             '--fiducial_sample_spacing=0.1 ' +
             '--samples_between_reref=200 ' +
             '--raft_center_x=190 ' +
             '--raft_center_y=90 ' +
             '--raft_theta=0 ' +
             ' > ' raft_id + '_scan_plan.txt'

subprocess.check_call(commandstr, shell=True)

# Below the Perl script executes the scan plan.
# N.B. The path to the scripts needs to be defined relative to the installation directory

commandstr = 'ln -sf /lnfs/lsst/data/ccs/ts5/default_ts5_scanplan ' + raft_id + '_scan_plan.txt'

commandstr = 'perl /u/gl/digel/lsst/IandT-jobs/harnessed_jobs/ts5_scan/v0/slac_ts5_dlog.perl --input_file=' +
              raft_id + '_scan_plan.txt'

subprocess.check_call(commandstr, shell=True)
