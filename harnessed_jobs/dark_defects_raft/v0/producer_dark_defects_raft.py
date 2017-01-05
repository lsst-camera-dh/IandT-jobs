#!/usr/bin/env python
"""
Producer script for raft-level dark defects analysis.
"""
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
    sflat_files = siteUtils.dependency_glob('S*/%s_sflat_500_flat_H*.fits' % sensor_id,
                                            jobname='sflat_raft_acq_sim',
                                            description='Superflat files:')
    mask_files = \
        eotestUtils.glob_mask_files(pattern='%s_*mask.fits' % sensor_id)

    task = sensorTest.DarkPixelsTask()
    task.run(sensor_id, sflat_files, mask_files)
