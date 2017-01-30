#!/usr/bin/env python
""" Producer script """
import os
import camera_components
from simulation.fake_raft import copy_single_sensor_data
import siteUtils

# These are specific to this test
TESTTYPE = 'TRAP'
IMGTYPES = ['BIAS', 'PPUMP']
PROCESS_NAME_IN = os.environ.get('LCATR_PROCESS_NAME_IN', 'ppump_raft_acq')
PATTERN = '*_trap*.fits'
OUTPATH = '.'
RAFT_ID = siteUtils.getUnitId()

RAFT = camera_components.Raft.create_from_etrav(RAFT_ID)

for image_type in IMGTYPES:
    copy_single_sensor_data(RAFT, PROCESS_NAME_IN, OUTPATH,
                            test_type=TESTTYPE, image_type=image_type,
                            pattern=PATTERN, sort=True)
