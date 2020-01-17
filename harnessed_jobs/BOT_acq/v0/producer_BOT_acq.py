#!/usr/bin/env python
"""
Producer script for BOT_acq harnessed job.

This just runs the bot-data.py acquisition script from the ccs account,
passing that script the appropriate configuration file for the
acquisition.
"""
import os
import sys
import shutil
import subprocess
import pathlib
import siteUtils

# Check if acq_run is set in the lcatr.cfg file.  If so, then do not
# run an acquisition here since downstream analysis tasks will use
# data acquired in that run.
if 'LCATR_ACQ_RUN' in os.environ:
    sys.exit(0)

run_number = siteUtils.getRunNumber()
job_id = os.environ['LCATR_JOB_ID']

acq_config = siteUtils.get_job_acq_configs()
bot_eo_acq_cfg = acq_config['bot_eo_acq_cfg']
outfile = os.path.basename(bot_eo_acq_cfg).replace('.cfg', '') \
          + f'_{run_number}_{job_id}.cfg'
shutil.copy(bot_eo_acq_cfg, os.path.join('.', outfile))

command = '/home/ccs/bot-data.py --symlink . --run {} {}'\
    .format(run_number, bot_eo_acq_cfg)
subprocess.check_call(command, shell=True)

pathlib.Path('PRESERVE_SYMLINKS').touch()
