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
                                   jobname=siteUtils.getProcessName('ts5_scan'),
                                   description='')[0]

print('----')
print(infile)
print('----')

# Run Andy's parsing script (Perl)
# This involves picking up the value for the KFrame flag ('1' or '2') from
# the ts5_opts.cfg # file pointed to by LCATR_TS5_OPTS
ts5_options_file = os.environ['LCATR_TS5_OPTS']

for line in open(ts5_options_file):
    if 'TS5_PARSE_KFRAME_ID' in line:
	kframe = line.split('=')[1][:-1]

# Find a representative temperature in the scan data file
with open(infile, 'r') as f:
    line = f.readline()
    while '# TF theta' not in line:
        line = f.readline()

    data_line = f.readline()
f.closed
temperature = data_line.split()[5]
print('Temperature:  ' + temperature)

flag = ' --cold '
if float(temperature) > 0:
    flag = ' --warm '

commandstr = 'perl ' + os.path.dirname(__file__) + '/slac_ts5_parse_scan.perl --KFrame ' + \
             kframe + ' ' + infile

print('kframe = ' + kframe)

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)

# Run Andy's analysis script (Perl) to generate the various data products
# N.B. The path needs to be defined relative to the installatio directory and the name of the 
# N.B. Andy is adding temperature readings to the scan data file, so the (assumed) temperature
# will not need to be a command-line argument as below.

# construct the name of the processed scan file
processed_scan_file = os.path.basename(infile) + '__ms.tnt'

commandstr = 'perl ' + os.path.dirname(__file__) + '/slac_ts5_scan_results.perl' + flag + processed_scan_file + \
             ' ' + temperature

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)
