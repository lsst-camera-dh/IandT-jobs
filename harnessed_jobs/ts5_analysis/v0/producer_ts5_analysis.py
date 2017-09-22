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
infile = siteUtils.dependency_glob('*data.txt',
                                   jobname=siteUtils.getProcessName('ts5_scan'),
                                   description='')[0]

# Run Andy's parsing script (Perl)
# This involves picking up the value for the KFrame flag ('1' or '2') from
# the ts5_opts.cfg file pointed to by LCATR_TS5_OPTS
ts5_options_file = os.environ['LCATR_TS5_OPTS']

for line in open(ts5_options_file):
    if 'TS5_PARSE_KFRAME_ID' in line:
        # The [:-1] below removes the \n newline character
	kframe = line.split('=')[1][:-1]

# Also find a representative temperature in the scan data file
# (The Perl script does not particularly care about the temperature
# but uses it as a label in plots.)
with open(infile, 'r') as f:
    line = f.readline()
    while '# TF theta' not in line:
        line = f.readline()

    data_line = f.readline()
f.closed
temperature = data_line.split()[5]

flag = ' --cold '
if float(temperature) > 0:
    flag = ' --warm '

commandstr = 'perl ' + os.path.dirname(__file__) + '/slac_ts5_parse_scan.perl --KFrame ' + \
             kframe + ' ' + infile

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)

# Run Andy's analysis script (Perl) to generate the various data products

# Construct the name of the processed scan file (to be written to the
# current working directory with the same name as the scan data file +
# '__ms.txt' appended
processed_scan_file = os.path.basename(infile) + '__ms.txt'

commandstr = 'perl ' + os.path.dirname(__file__) + '/slac_ts5_scan_results.perl' + flag + processed_scan_file + \
             ' ' + temperature

print('Executing:  ' + commandstr)
subprocess.check_call(commandstr, shell=True)
