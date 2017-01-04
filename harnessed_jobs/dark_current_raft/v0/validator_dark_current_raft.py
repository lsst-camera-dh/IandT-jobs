#!/usr/bin/env python
import lsst.eotest.sensor as sensorTest
import lcatr.schema
import siteUtils
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
    data = sensorTest.EOTestResults(results_file)

    amps = data['AMP']
    dc95s = data['DARK_CURRENT_95']
    for amp, dc95 in zip(amps, dc95s):
        results.append(lcatr.schema.valid(lcatr.schema.get('dark_current_raft'),
                                          amp=amp, dark_current_95CL=dc95,
                                          slot=slots[sensor_id],
                                          sensor_id=sensor_id))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
