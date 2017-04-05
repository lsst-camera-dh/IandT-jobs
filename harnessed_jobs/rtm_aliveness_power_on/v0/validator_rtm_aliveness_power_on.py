#!/usr/bin/env python
from __future__ import print_function
import os
import glob
import shutil
import socket
import datetime
import matplotlib.pyplot as plt
import lcatr.schema
import siteUtils
import ccs_trending

job_dir = siteUtils.getJobDir()

host = os.getenv('LCATR_CCS_HOST', 'lsst-mcm')
time_axis = ccs_trending.TimeAxis(dt=0.5, nbins=200)
config_file = os.path.join(os.environ['IANDTJOBSDIR'], 'harnessed_jobs',
                           'rtm_aliveness_power_on', 'v0',
                           'rtm_aliveness_power_plots.cfg')
config = ccs_trending.ccs_trending_config(config_file)
print("Making trending plots")
local_time = datetime.datetime.now().isoformat()[:len('2017-01-24T10:44:00')]
for section in config.sections():
    print("  processing", section)
    plotter = ccs_trending.TrendingPlotter('ts8', host, time_axis=time_axis)
    plotter.read_config(config, section)
    plotter.plot()
    plt.savefig('%s_%s_%s.png' % (section, local_time, siteUtils.getUnitId()))

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
