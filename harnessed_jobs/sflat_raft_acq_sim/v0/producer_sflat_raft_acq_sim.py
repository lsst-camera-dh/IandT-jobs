#!/usr/bin/env python
""" Producer script """

from simulation import fake_raft

# These are specific to this test
TESTTYPE = 'SFLAT_500'
IMGTYPES = ['FLAT']
PROCESS_NAME_IN = 'vendorIngest'
PATTERN = '*_sflat_500*.fits'

RAFT = fake_raft.Raft.create_from_etrav(fake_raft.RAFT_ID)

for image_type in IMGTYPES:
    RAFT.file_copy(PROCESS_NAME_IN, fake_raft.OUTPATH,
                   test_type=TESTTYPE, image_type=image_type,
                   pattern=PATTERN, sort=True)
