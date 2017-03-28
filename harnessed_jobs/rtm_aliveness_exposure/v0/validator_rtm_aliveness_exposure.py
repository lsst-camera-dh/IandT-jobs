#!/usr/bin/env python
import os
import glob
import shutil
import lcatr.schema
import siteUtils

job_dir = siteUtils.getJobDir()

#shutil.copy(os.path.join(job_dir, 'rebalive_plots.gp'), os.getcwd())
#shutil.copy(os.path.join(job_dir, 'rebalive_plots.sh'), os.getcwd())
#shutil.copy(os.path.join(job_dir, 'plotchans.list'), os.getcwd())

results = []

files = glob.glob("*.txt")
files = files + glob.glob("*summary*")
files = files + glob.glob("*png")
files = files + glob.glob("*log*")

data_products = [lcatr.schema.fileref.make(item) for item in files]
results.extend(data_products)

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
