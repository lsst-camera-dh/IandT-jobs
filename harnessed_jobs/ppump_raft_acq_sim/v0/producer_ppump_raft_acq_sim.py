#!/usr/bin/env python
""" Producer script """

from simulation import fake_raft
import siteUtils

# These are specific to this test
TESTTYPE = 'TRAP'
IMGTYPES = ['BIAS', 'PPUMP']
PROCESS_NAME_IN = 'vendorIngest'
PATTERN = '*_trap*.fits'
OUTPATH = '.'
RAFT_ID = siteUtils.getUnitId()

RAFT = fake_raft.Raft.create_from_etrav(RAFT_ID)

for image_type in IMGTYPES:
    RAFT.file_copy(PROCESS_NAME_IN, OUTPATH,
                   test_type=TESTTYPE, image_type=image_type,
                   pattern=PATTERN, sort=True)