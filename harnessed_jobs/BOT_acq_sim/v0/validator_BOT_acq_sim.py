#!/usr/bin/env python
""" Validator script """
import os
import glob
import time
import lcatr.schema
import siteUtils

results = []

if 'LCATR_ACQ_RUN' not in os.environ:
    files = sorted(glob.glob(os.path.join('.', '*', '*.fits')))
    t0 = time.time()
    results.extend([lcatr.schema.fileref.make(item) for item in files])
    print('time to make filerefs:', (time.time() - t0)/60., 'mins')

results.extend(siteUtils.jobInfo())

t0 = time.time()
lcatr.schema.write_file(results)
print('time to write summary.lims:', (time.time() - t0)/60., 'mins')
t0 = time.time()
lcatr.schema.validate_file()
print('time to validate summary.lims:', (time.time() - t0)/60., 'mins')
