#!/usr/bin/env python
"""
Producer script for BOT_acq harnessed job.

This just runs the bot-data.py acquisition script from the ccs account,
passing that script the appropriate configuration file for the
acquisition.
"""
import os
import sys
import json
import shutil
import subprocess
import pathlib
import siteUtils
from bot_acq_retry import copy_exposure_symlinks


def copy_sequencer_files():
    """
    Run ccs_get_sequencer_paths.py script to get sequencer files. Copy
    these files via scp to the current working directory.
    """
    json_file = 'sequencer_paths.json'
    my_ccs_script = os.path.join(os.environ['IANDTJOBSDIR'], 'harnessed_jobs',
                                 'BOT_acq', 'v0', 'ccs_get_sequencer_paths.py')
    command = f'/lsst/ccs/prod/bin/ccs-script {my_ccs_script} {json_file}'
    subprocess.check_call(command, shell=True)
    with open(json_file, 'r') as fd:
        seq_paths = json.load(fd)
    for _, value in seq_paths.items():
        command = f'scp {value} .'
        print(command)
        subprocess.check_call(command, shell=True)


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

copy_sequencer_files()
skip = os.environ.get('LCATR_SKIP_EXPOSURES', copy_exposure_symlinks())

command = (f'/home/ccs/bot-data.py --symlink . --skip {skip} '
           f'--run {run_number} {bot_eo_acq_cfg}')

print("executing: {command}")
subprocess.check_call(command, shell=True)

pathlib.Path('PRESERVE_SYMLINKS').touch()
