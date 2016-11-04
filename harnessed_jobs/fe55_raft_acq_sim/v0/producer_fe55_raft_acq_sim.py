#!/usr/bin/env python

import os
import siteUtils
from simulation import fake_raft


# These are specific to this test
TESTTYPE = 'FE55'
IMGTYPE = 'BIAS'
PROCESS_NAME_IN = 'vendorIngest'
PATTERN = '*_fe55*.fits'

RAFT = fake_raft.Raft.create_from_etrav(fake_raft.RAFT_ID)

RAFT.file_copy(PROCESS_NAME_IN, fake_raft.OUTPATH, 
               test_type=TESTTYPE, image_type=IMGTYPE,
               pattern=PATTERN)
