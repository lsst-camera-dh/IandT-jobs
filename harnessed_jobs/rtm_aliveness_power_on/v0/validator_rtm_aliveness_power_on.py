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
import ccsTools
import ccs_trending

job_dir = siteUtils.getJobDir()
ts8 = ccsTools.ccs_subsystem_mapping()['ts8']

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
    try:
        plotter = ccs_trending.TrendingPlotter(ts8, host, time_axis=time_axis)
        plotter.read_config(config, section)
        plotter.plot()
        plt.savefig('%s_%s_%s.png' % (section, local_time,
                                      siteUtils.getUnitId()))
    except Exception as eobj:
        print("Exception caught while producing trending plot:")
        print(str(eobj))
        print("continuing...")

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
