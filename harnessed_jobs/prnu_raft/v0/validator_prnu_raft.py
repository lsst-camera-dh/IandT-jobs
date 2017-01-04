#!/usr/bin/env python
import astropy.io.fits as fits
import numpy as np
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
    sensor_id = str(sensor_id)
    ccd_vendor = sensor_id.split('-')[0]

    results_file = '%s_eotest_results.fits' % sensor_id
    prnu_results = fits.open(results_file)['PRNU_RESULTS'].data

    for wl, stdev, mean in zip(prnu_results['WAVELENGTH'],
                               prnu_results['STDEV'], prnu_results['MEAN']):
        results.append(lcatr.schema.valid(lcatr.schema.get('prnu'),
                                          wavelength=int(np.round(wl)),
                                          pixel_stdev=stdev, pixel_mean=mean,
                                          slot=slots[sensor_id],
                                          sensor_id=sensor_id))

        qe_acq_job_id = \
            siteUtils.get_prerequisite_job_id('S*/%s_lambda_flat_*.fits' % sensor_id,
                                              jobname='qe_raft_acq_sim')
        md = dict(illumination_non_uniformity_file=dict(JOB_ID=qe_acq_job_id))
        results.extend(eotestUtils.eotestCalibsPersist('illumination_non_uniformity_file',
                                                       metadata=md))

results.append(siteUtils.packageVersions())
results.extend(siteUtils.jobInfo())
results.append(eotestUtils.eotestCalibrations())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
