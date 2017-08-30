#!/usr/bin/env python
# from ccsTools import ccsProducer
import subprocess

# ccsProducer('ts5_scan', 'TS5-PulseScan.py')

# Below the Perl script executes the scan plan that has already been
# written.  The paths to the Perl script and the scan plan need to
# be hardwired.

subprocess.check_call('perl <full path to perl script> <command line arguments>', shell=True)
