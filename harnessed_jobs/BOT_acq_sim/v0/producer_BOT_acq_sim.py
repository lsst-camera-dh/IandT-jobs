#!/usr/bin/env python
""" Producer script """
import os
from simulation import fake_camera
import time
import siteUtils

# This is the generic "fake" BOT, which maps rafts to slots
RAFTMAP_YAML = os.path.join(os.path.dirname(fake_camera.__file__), 'test_bot.yaml')
fake_cam = fake_camera.FakeCamera.create_from_yaml(RAFTMAP_YAML)

# These are specific to one run
ARGS_DICT = dict(root_folder_out='test_data')

# These are specific to this test
ACQ_TYPES = ['dark_raft_acq']

for acq_type in ACQ_TYPES:
    ARGS_DICT['acq_type_in'] = acq_type
    fake_cam.run(**ARGS_DICT)

