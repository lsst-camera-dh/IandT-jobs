#!/usr/bin/env python
from __future__ import print_function
import lsst.eotest.sensor as sensorTest
import siteUtils
import eotestUtils
import simulation.fake_raft

siteUtils.aggregate_job_ids()

raft_id = siteUtils.getUnitId()
db_name = 'Dev'
raft = simulation.fake_raft.Raft.create_from_etrav(raft_id, db_name=db_name)

for sensor_id in raft.sensor_names:
    sensor_id = str(sensor_id)
    dark_files = siteUtils.dependency_glob('S*/%s_dark_dark_*.fits' % sensor_id,
                                           jobname='dark_raft_acq_sim',
                                           description='Dark files:')
    mask_files = \
        eotestUtils.glob_mask_files(pattern='%s_*mask.fits' % sensor_id)
    gains = eotestUtils.getSensorGains(jobname='fe55_raft_analysis',
                                       sensor_id=sensor_id)

    task = sensorTest.BrightPixelsTask()
    task.run(sensor_id, dark_files, mask_files, gains)
