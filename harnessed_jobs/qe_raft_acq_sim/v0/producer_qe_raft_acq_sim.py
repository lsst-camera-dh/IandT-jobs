#!/usr/bin/env python
""" Producer script """

import camera_components
from simulation.fake_raft import copy_single_sensor_data
import siteUtils

# These are specific to this test
TESTTYPE = 'LAMBDA'
IMGTYPES = ['BIAS', 'FLAT']
PROCESS_NAME_IN = 'vendorIngest'
PATTERN = '*_lambda*.fits'
OUTPATH = '.'
RAFT_ID = siteUtils.getUnitId()

RAFT = camera_components.Raft.create_from_etrav(RAFT_ID)

for image_type in IMGTYPES:
    copy_single_sensor_data(RAFT, PROCESS_NAME_IN, OUTPATH,
                            test_type=TESTTYPE, image_type=image_type,
                            pattern=PATTERN, sort=True)
