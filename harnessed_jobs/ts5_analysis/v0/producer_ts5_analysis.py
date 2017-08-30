#!/usr/bin/env python
import sys
import os
import siteUtils
import subprocess

raft_id = siteUtils.getUnitId()

# Find the TS5 metrology scan data by constructing the name of the data-taking step
acqjobname = siteUtils.getJobName().replace('analysis', 'scan')

print('ts5_analysis:')
print(acqjobname)
print(siteUtils.getProcessName(acqjobname))
print('----')

# siteUtils returns a list with one member;
# here take the first (and only) member
infile = siteUtils.dependency_glob('*.csv',
                                   jobname=siteUtils.getProcessName(acqjobname),
                                   description='')[0]

# Run Andy's Perl analysis script
subprocess.check_call('perl <full path to perl script> <command line arguments>', shell=True)
