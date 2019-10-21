#!/usr/bin/env python
""" Producer script """
import os
import sys
import subprocess
from configparser import SafeConfigParser
import siteUtils
from simulation import fake_camera

if 'LCATR_ACQ_RUN' in os.environ:
    sys.exit(0)

command = 'ln -s /gpfs/slac/lsst/fs3/g/data/jchiang/BOT_testing/BOT_acq_6549D/* .'
subprocess.check_call(command, shell=True)
subprocess.check_call('touch PRESERVE_SYMLINKS', shell=True)
sys.exit(0)

# This is the generic "fake" BOT, which maps rafts to slots
RAFTMAP_YAML = os.path.join(os.environ['LCATR_CONFIG_DIR'], 'test_bot.yaml')
IMAGE_TYPE_DICT_YAML = os.path.join(os.environ['LCATR_CONFIG_DIR'], 'image_type_map.yaml')

fake_cam = fake_camera.FakeCamera.create_from_yaml(RAFTMAP_YAML)

# These are specific to one run
ARGS_DICT = dict(root_folder_out='.',
                 image_type_dict_yaml=IMAGE_TYPE_DICT_YAML,
                 dry_run=False)

# Mapping of acquisition type to harnessed job names. Commented out
# entries do not yet have harnessed jobs implemented.
JOB_NAMES = {
    'bias': 'bias_raft_acq',
    'fe55': 'fe55_raft_acq',
    'dark': 'dark_raft_acq',
    'persistence': 'persistence_raft_acq',
    'sflat': 'sflat_raft_acq',
    'lambda': 'qe_raft_acq',
    'flat': 'flat_pair_raft_acq',
    'scan': 'scan_mode_acq',
    'ppump': 'ppump_raft_acq',
    }


# Find the raft-level EO configuration file.
acq_config = siteUtils.get_job_acq_configs()
ACQ_SIM_CONFIG_FILE = acq_config['bot_eo_acq_cfg']

# Read in the acquisition sequence.
ACQS = []
scp = SafeConfigParser(allow_no_value=True, inline_comment_prefixes=("#", ))
scp.optionxform = str   # allow for case-sensitive keys
scp.read(ACQ_SIM_CONFIG_FILE)
for acq_type, acq_val in scp.items("ACQUIRE"):
    ACQS.append(acq_type)

# Loop over the acquisition types
for acq_type in ACQS:
    ARGS_DICT['acq_type_in'] = JOB_NAMES[acq_type]
    fake_cam.run(**ARGS_DICT)
