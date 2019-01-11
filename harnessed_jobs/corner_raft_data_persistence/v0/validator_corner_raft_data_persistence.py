#!/usr/bin/env python
import os
import glob
import lcatr.schema

results = []

folders = sorted(glob.glob('*_acq'))
for folder in folders:
    fits_files = sorted(glob.glob(os.path.join(folder, '*.fits')))
    results.extend([lcatr.schema.fileref.make(item) for item in fits_files])

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
