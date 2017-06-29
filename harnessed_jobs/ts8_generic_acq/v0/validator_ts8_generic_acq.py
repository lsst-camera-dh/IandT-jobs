#!/usr/bin/env python
"""
Validator script for ts8_generic_acq harnessed job.
"""
import os
import shutil
import lcatr.schema
import siteUtils
from ccsTools import ccsValidator

# Copy the rtmacqcfgfile to the working directory, and persist it.
acq_cfg = os.path.join(siteUtils.configDir(), 'acq.cfg')
with open(acq_cfg) as fobj:
    for line in fobj:
        if line.startswith('rtmacqcfgfile'):
            image_sequence_file = line.strip().split('=')[1].strip()
shutil.copy(image_sequence_file, '.')

results = [lcatr.schema.fileref.make(os.path.basename(image_sequence_file))]

ccsValidator(results)
