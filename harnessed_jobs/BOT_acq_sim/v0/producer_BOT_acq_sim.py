#!/usr/bin/env python
""" Producer script """
import os
from simulation import fake_camera
import time
import siteUtils
import yaml
from configparser import SafeConfigParser

# This is the generic "fake" BOT, which maps rafts to slots
RAFTMAP_YAML = os.path.join(os.environ['LCATR_CONFIG_DIR'], 'test_bot.yaml')
fake_cam = fake_camera.FakeCamera.create_from_yaml(RAFTMAP_YAML)

# These are specific to one run
ARGS_DICT = dict(root_folder_out='.')

# Mapping of acquisition type to harnessed job names. Commented out
# entries do not yet have harnessed jobs implemented.
JOB_NAMES = {
    'bias': 'bias_raft_acq',
    'fe55': 'fe55_raft_acq',
    'dark': 'dark_raft_acq',
    'persistence': 'persistence_raft_acq',
    'sflat': 'sflat_raft_acq',
    'lambda': 'qe_raft_acq',
    'flat': 'flat_raft_acq',
    'scan': 'scan_mode_acq',
    'ppump': 'ppump_raft_acq',
    }


# Find the raft-level EO configuration file.
with open(os.path.join(os.environ['LCATR_CONFIG_DIR'], 'acq.cfg'), 'r') as fd:
    for line in fd:
        if line.startswith('bot_eo_acq_cfg'):
            ACQ_SIM_CONFIG_FILE = line.strip().split('=')[1].strip()
            break

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

