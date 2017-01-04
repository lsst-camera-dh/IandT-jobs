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

    trap_file = '%s_traps.fits' % sensor_id
    eotestUtils.addHeaderData(trap_file, LSST_NUM=sensor_id, TESTTYPE='TRAP',
                              DATE=eotestUtils.utc_now_isoformat(),
                              CCD_MANU=ccd_vendor.upper())
    results.append(lcatr.schema.fileref.make(trap_file))

    mask_file = '%s_traps_mask.fits' % sensor_id
    results.append(lcatr.schema.fileref.make(mask_file))

    results_file = '%s_eotest_results.fits' % sensor_id
    data = sensorTest.EOTestResults(results_file)
    amps = data['AMP']
    num_traps = data['NUM_TRAPS']

    for amp, ntrap in zip(amps, num_traps):
        results.append(lcatr.schema.valid(lcatr.schema.get('traps'),
                                          amp=amp, num_traps=ntrap,
                                          slot=slots[sensor_id],
                                          sensor_id=sensor_id))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
