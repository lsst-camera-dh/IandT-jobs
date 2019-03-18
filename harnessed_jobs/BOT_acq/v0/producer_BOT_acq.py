#!/usr/bin/env python
"""
Producer script for BOT_acq harnessed job.

This just runs the bot-data.py acquisition script from the ccs account,
passing that script the appropriate configuration file for the
acquisition.
"""
import subprocess
import pathlib
import siteUtils

run_number = siteUtils.getRunNumber()

acq_config = siteUtils.get_job_acq_configs()

command = '/home/ccs/bot-data.py --symlink . --run {} {}'\
    .format(run_number, acq_config['bot_eo_acq_cfg'])

subprocess.check_call(command, shell=True)
pathlib.Path('PRESERVE_SYMLINKS').touch()
