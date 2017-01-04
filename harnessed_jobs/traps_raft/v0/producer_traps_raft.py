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
    trap_file = siteUtils.dependency_glob('S*/%s_trap_ppump_*.fits' % sensor_id,
                                          jobname='ppump_raft_acq_sim',
                                          description='Trap file:')[0]
    mask_files = \
        eotestUtils.glob_mask_files(pattern='%s_*mask.fits' % sensor_id)
    # Omit rolloff defects mask since a trap in the rolloff edge region can
    # affect the entire column.
    mask_files = [item for item in mask_files
                  if item.find('rolloff_defects') == -1]
    print("Using mask files:")
    for mask_file in mask_files:
        print("  " + mask_file)

    gains = eotestUtils.getSensorGains(jobname='fe55_raft_analysis',
                                       sensor_id=sensor_id)

    task = sensorTest.TrapTask()
    task.run(sensor_id, trap_file, mask_files, gains)

