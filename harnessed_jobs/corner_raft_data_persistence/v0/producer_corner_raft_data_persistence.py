#!/usr/bin/env python
import os
import glob
from copy_files import copy_files

cr_eo_dir = os.environ['LCATR_CR_EO_DIR']

acq_dirs = sorted(glob.glob(os.path.join(cr_eo_dir, '*_acq')))

for acq_dir in acq_dirs:
    output_folder = os.path.basename(acq_dir)
    os.makedirs(output_folder, exisit_ok=True)
    fits_files = sorted(glob.glob(os.path.join(acq_dir, '*.fits')))
    copy_files(fe55_bias, output_folder)
