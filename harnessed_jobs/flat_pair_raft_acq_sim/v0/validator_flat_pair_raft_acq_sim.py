#!/usr/bin/env python
""" Validator script """

import glob
import lcatr.schema
from simulation import fake_raft

PATTERN = '*_flat*.fits'

OUTREGEXP = fake_raft.make_outfile_path(outpath=fake_raft.OUTPATH, slot_name="*",
                                        file_string=PATTERN, job_id=fake_raft.JOB_ID)

RESULTS = []
FILES = sorted(glob.glob(OUTREGEXP))
DATA_PRODUCTS = [lcatr.schema.fileref.make(item) for item in FILES]

RESULTS.extend(DATA_PRODUCTS)
lcatr.schema.write_file(RESULTS)
lcatr.schema.validate_file()
