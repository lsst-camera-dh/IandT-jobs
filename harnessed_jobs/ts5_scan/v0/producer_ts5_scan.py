#!/usr/bin/env python
# from ccsTools import ccsProducer
import subprocess
#import siteUtils

#raft_id = siteUtils.getUnitId()
raft_id = 'LCA-10753_ETU2'

# Set up the command for the subprocess call to generate the scan plan file
# N.B. The path to the scripts needs to be defined relative to the installation directory
commandstr = 'perl /lnfs/lsst/devel/digel/IandT-jobs/harnessed_jobs/ts5_scan/v0/slac_ts5_metro_scan.perl ' + \
             '--sensor_sample_spacing=0.5 ' + \
             '--fiducial_sample_spacing=0.5 ' + \
             '--samples_between_reref=200 ' + \
             '--raft_center_x=9.2 ' + \
             '--raft_center_y=-15 ' + \
             '--raft_theta=0.173 ' + \
	     '--selfcal -0.5:-0.25:0:0.2350:0.5 ' + \
             '> ' + raft_id + '_scan_plan.txt'

subprocess.check_call(commandstr, shell=True)

# Below the Perl script executes the scan plan.
# N.B. The path to the scripts needs to be defined relative to the installation directory

#commandstr = 'ln -sf /lnfs/lsst/data/ccs/ts5/default_ts5_scanplan ' + raft_id + '_scan_plan.txt'

commandstr = 'perl /lnfs/lsst/devel/digel/IandT-jobs/harnessed_jobs/ts5_scan/v0/slac_ts5_dlog.perl --input_file=' + \
              raft_id + '_scan_plan.txt --output_filename_root=' + raft_id + ' --keyence_sampletime_par=6 --keyence_filter_nsample=5 --verbose --keyence_out1_maskpars=0.7:-0.7 --keyence_out2_maskpars=1.7:-1.7'

subprocess.check_call(commandstr, shell=True)
