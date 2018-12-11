#!/usr/bin/env python
"""
Validator script for BOT aliveness test acquisitions.
"""
import os
import glob
import lcatr.schema

fits_files = sorted(glob.glob(os.path.join(., '*.fits')))
results = [lcatr.schema.fileref.make(item) for item in fits_files]

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
