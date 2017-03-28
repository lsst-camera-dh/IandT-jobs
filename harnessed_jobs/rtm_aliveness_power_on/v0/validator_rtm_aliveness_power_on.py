#!/usr/bin/env python
from __future__ import print_function
import os
import glob
import shutil
import socket
import lcatr.schema
import siteUtils
import ccs_trending

job_dir = siteUtils.getJobDir()

#host = socket.gethostname()
host = 'lsst-mcm:8080'
time_axis = ccs_trending.TimeAxis(dt=0.5, nbins=200)
config_file = os.path.join(os.environ['IANDTJOBSDIR'], 'harnessed_jobs',
                           'rtm_aliveness_power_on', 'v0',
                           'rtm_aliveness_power_on_plots.cfg')
config = ccs_trending.ccs_trending_config(config_file)
print("Making trending plots")
for section in config.sections():
    print("  processing", section)
    plotter = ccs_trending.TrendingPlotter('ts8', host, time_axis=time_axis)
    plotter.read_config(config, section)
    plotter.plot()
    plt.savefig('%s_%s_%s.png' % (section, rebUtils.local_time(), 

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
