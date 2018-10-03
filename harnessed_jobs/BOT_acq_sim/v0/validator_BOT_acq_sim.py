#!/usr/bin/env python
""" Validator script """

import os
import glob
import lcatr.schema
import siteUtils
import time
from simulation import fake_camera

# These are specific to one run
ARGS_DICT = dict(root_folder_out='test_data')

# These are specific to this test
OUTREGEXP = os.path.join(fake_camera.make_output_topdir_path(**ARGS_DICT), '*')

RESULTS = []
DIRS = sorted(glob.glob(OUTREGEXP))
FILES = []
for DIR in DIRS:
    FILES += sorted(glob.glob(os.path.join(DIR, '*.fits')))
DATA_PRODUCTS = [lcatr.schema.fileref.make(item) for item in FILES]

RESULTS.extend(DATA_PRODUCTS)
lcatr.schema.write_file(RESULTS)
lcatr.schema.validate_file()
