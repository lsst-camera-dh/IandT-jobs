#!/usr/bin/env python
"""
Producer script for BOT aliveness test acquisitions.
"""
import os
import subprocess

# Find the top-level acquisition configuration file.
with open(os.path.join(os.environ['LCATR_CONFIG_DIR'], 'acq.cfg'), 'r') as fd:
    for line in fd:
        if line.startswith('bot_aliveness_acq_cfg'):
            cfg_file = line.strip().split('=')[1].strip()
            break

run_number = os.environ['LCATR_RUN_NUMBER']

command = '/home/ccs/bot-data.py --symlink . --run {} {}'.format(run_number,
                                                                 cfg_file)
subprocess.check_call(command)
