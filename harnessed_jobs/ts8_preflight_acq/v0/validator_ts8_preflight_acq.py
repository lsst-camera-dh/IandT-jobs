#!/usr/bin/env python
import glob
import lcatr.schema

fits_files = glob.glob('*.fits')
txt_files = glob.glob('pd-values*.txt')
png_files = glob.glob('pd-values*.png')

results = []

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
