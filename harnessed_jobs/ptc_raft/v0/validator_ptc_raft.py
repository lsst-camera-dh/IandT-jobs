#!/usr/bin/env python
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
    sensor_id = str(sensor_id)
    ccd_vendor = sensor_id.split('-')[0]

    ptc_results = '%s_ptc.fits' % sensor_id
    eotestUtils.addHeaderData(ptc_results, LSST_NUM=sensor_id, TESTTYPE='FLAT',
                              DATE=eotestUtils.utc_now_isoformat(),
                              CCD_MANU=ccd_vendor.upper())

    results.append(lcatr.schema.fileref.make(ptc_results))

    results_file = '%s_eotest_results.fits' % sensor_id
    data = sensorTest.EOTestResults(results_file)
    amps = data['AMP']
    ptc_gains = data['PTC_GAIN']
    ptc_gain_errors = data['PTC_GAIN_ERROR']
    for amp, gain, gain_error in zip(amps, ptc_gains, ptc_gain_errors):
        results.append(lcatr.schema.valid(lcatr.schema.get('ptc_raft'),
                                          amp=amp, ptc_gain=gain,
                                          ptc_gain_error=gain_error,
                                          slot=slots[sensor_id],
                                          sensor_id=sensor_id))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
