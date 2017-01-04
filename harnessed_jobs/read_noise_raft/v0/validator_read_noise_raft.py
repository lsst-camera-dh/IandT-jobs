#!/usr/bin/env python
from __future__ import print_function
import glob
import lsst.eotest.sensor as sensorTest
import lcatr.schema
import siteUtils
import eotestUtils
import simulation.fake_raft

raft_id = siteUtils.getUnitId()
db_name = 'Dev'

raft = simulation.fake_raft.Raft.create_from_etrav(raft_id, db_name=db_name)
slots = dict((str(x[1]), str(x[0])) for x in raft.items())

results = []
for sensor_id in raft.sensor_names:
    ccd_vendor = sensor_id.split('-')[0]
    read_noise_file = '%s_eotest_results.fits' % sensor_id
    data = sensorTest.EOTestResults(read_noise_file)
    amps = data['AMP']
    read_noise_data = data['READ_NOISE']
    system_noise_data = data['SYSTEM_NOISE']
    total_noise_data = data['TOTAL_NOISE']
    for amp, read_noise, system_noise, total_noise in zip(amps, read_noise_data,
                                                          system_noise_data,
                                                          total_noise_data):
        results.append(lcatr.schema.valid(lcatr.schema.get('read_noise_raft'),
                                          amp=amp, read_noise=read_noise,
                                          system_noise=system_noise,
                                          total_noise=total_noise,
                                          slot=slots[sensor_id],
                                          sensor_id=sensor_id))

    fe55_acq_job_id = siteUtils.get_prerequisite_job_id('S*/%s_fe55_fe55_*.fits' % sensor_id,
                                                        jobname='fe55_raft_acq_sim')
    md = dict(system_noise_file=dict(JOB_ID=fe55_acq_job_id))
    results.extend(eotestUtils.eotestCalibsPersist('system_noise_file',
                                                   metadata=md))

    files = glob.glob('%s_read_noise?*.fits' % sensor_id)
    for fitsfile in files:
        eotestUtils.addHeaderData(fitsfile, LSST_NUM=sensor_id, TESTTYPE='FE55',
                                  DATE=eotestUtils.utc_now_isoformat(),
                                  CCD_MANU=ccd_vendor.upper())

    data_products = [lcatr.schema.fileref.make(item) for item in files]
    results.extend(data_products)

results.extend(siteUtils.jobInfo())
results.append(eotestUtils.eotestCalibrations())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
