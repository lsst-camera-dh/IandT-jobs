#!/usr/bin/env python
import sys
import os
import siteUtils
import subprocess

print('ts5_analysis:')

raft_id = siteUtils.getUnitId()

# Find the TS5 metrology scan data from the data-taking step
# siteUtils returns a list with one member;
# here take the first (and only) member
infile = siteUtils.dependency_glob('__ms.tnt',
                                   jobname=siteUtils.getProcessName(ts5_scan'),
                                   description='')[0]

# Run Andy's parsing script (Perl)
# This involves picking up the value for the KFrame flag from an environment
# variable (assumes that .lcatr.cfg has had a line added to it
# kframe = 1
# or
# kframe = 2
kframe = os.environ['LCATR_KFRAME']
# N.B. Andy plans to have the equivalent of the kframe flag written to the scan data file
# so this setting of LCATR_KFRAME will no longer be necessary
# N.B. The path to the scripts needs to be defined relative to the installation directory

commandstr = 'perl /u/gl/digel/lsst/IandT-jobs/harnessed_jobs/ts5_analysis/v0/slac_ts5_parse_scan.perl --KFrame ' + 
             kframe + ' ' + infile

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)

# Run Andy's analysis script (Perl) to generate the various data products
# N.B. The path needs to be defined relative to the installatio directory and the name of the 
# N.B. Andy is adding temperature readings to the scan data file, so the (assumed) temperature
# will not need to be a command-line argument as below.

commandstr = 'perl /u/gl/digel/lsst/IandT-jobs/harnessed_jobs/ts5_analysis/v0/slac_ts5_scan_results.perl --cold ' + infile +
             ' -95'

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)
