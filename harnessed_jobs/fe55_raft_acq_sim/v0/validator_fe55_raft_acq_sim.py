#!/usr/bin/env python
import os
import glob

import siteUtils
import lcatr.schema
from simulation import fake_raft

PATTERN = '*_fe55*.fits'

OUTREGEXP = fake_raft.make_outfile_path(outpath=fake_raft.OUTPATH, slot_name="*", 
                                        file_string=PATTERN, job_id=fake_raft.JOB_ID)

results = []
files = sorted(glob.glob(OUTREGEXP))
data_products = [lcatr.schema.fileref.make(item) for item in files]

results.extend(data_products)
lcatr.schema.write_file(results)
lcatr.schema.validate_file()
