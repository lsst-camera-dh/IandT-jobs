#!/usr/bin/env python
"""
Validator script for BOT_acq harnessed job.
"""
import glob
import lcatr.schema
import siteUtils
from camera_components import camera_info

results = []

det_names = camera_info.get_det_names()
for det_name in det_names:
    fits_files = sorted(glob.glob('*/*_{}.fits'.format(det_name)))
    for item in fits_files:
        results.append(lcatr.schema.fileref.make(item))

pd_files = sorted(glob.glob('*/Photodiode_Readings.txt'))
results.extend([lcatr.schema.fileref.make(_) for _ in pd_files])

cfg_files = glob.glob('*.cfg')
results.extend([lcatr.schema.fileref.make(_) for _ in cfg_files])

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
