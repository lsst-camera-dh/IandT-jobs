#!/usr/bin/env python
""" Validator script """

import glob
import lcatr.schema
import siteUtils
from simulation import fake_raft

PATTERN = '*_flat*_*.fits'
OUTPATH = '.'
JOBNAME = siteUtils.getJobName()

OUTREGEXP = fake_raft.make_outfile_path(outpath=OUTPATH, slot_name="*",
                                        file_string=PATTERN, jobname=JOBNAME)

RESULTS = []
FILES = sorted(glob.glob(OUTREGEXP))
DATA_PRODUCTS = [lcatr.schema.fileref.make(item) for item in FILES]

RESULTS.extend(DATA_PRODUCTS)
lcatr.schema.write_file(RESULTS)
lcatr.schema.validate_file()
