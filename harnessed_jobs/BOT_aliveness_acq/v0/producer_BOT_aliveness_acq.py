#!/usr/bin/env python
"""
Producer script for BOT aliveness test acquisitions.
"""
import os
import subprocess

cfg_file = os.path.join(os.environ.get('LCATR_CONFIG_DIR', '.'),
                        'bot_aliveness_acq.cfg')
run_number = os.environ['LCATR_RUN_NUMBER']

command = './bot-data.py --symlink . --run {} {}'.format(run_number, cfg_file)
subprocess.check_call(command)
