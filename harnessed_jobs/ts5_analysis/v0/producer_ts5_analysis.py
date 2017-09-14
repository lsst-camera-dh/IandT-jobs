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
infile = siteUtils.dependency_glob('*.tnt',
                                   jobname=siteUtils.getProcessName(ts5_scan'),
                                   description='')[0]

# Run Andy's parsing script (Perl)
# This involves picking up the value for the KFrame flag from an environment
# variable (assumes that .lcatr.cfg has had a line added to it
# kframe = 1
# or
# kframe = 2
kframe = os.environ['LCATR_KFRAME']
# N.B. The path to the scripts needs to be defined relative to the installation directory
commandstr = 'perl /u/gl/digel/lsst/IandT-jobs/harnessed_jobs/ts5_analysis/v0/slac_ts5_parse_scan.perl --KFrame ' + 
             kframe + ' ' + infile

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)

# Run Andy's analysis script (Perl)
# N.B. The path needs to be defined relative to the installatio directory and the name of the 
commandstr = 'perl /u/gl/digel/lsst/IandT-jobs/harnessed_jobs/ts5_analysis/v0/slac_ts5_scan_results.perl --cold ' + infile +
             '__ms.tnt -95'

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)
