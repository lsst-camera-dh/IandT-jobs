#!/usr/bin/env python
from __future__ import print_function
import glob
import lcatr.schema
import siteUtils
import eotestUtils
import lsst.eotest.sensor as sensorTest
import simulation.fake_raft

raft_id = siteUtils.getUnitId()
db_name = 'Dev'
raft = simulation.fake_raft.Raft.create_from_etrav(raft_id, db_name=db_name)
slots = dict((str(x[1]), str(x[0])) for x in raft.items())

results = []
for sensor_id in raft.sensor_names:
    ccd_vendor = sensor_id.split('-')[0]
    # The output files from producer script.
    gain_file = '%(sensor_id)s_eotest_results.fits' % locals()
    psf_results = glob.glob('%(sensor_id)s_psf_results*.fits' % locals())[0]
    rolloff_mask = '%(sensor_id)s_rolloff_defects_mask.fits' % locals()

    output_files = gain_file, psf_results, rolloff_mask

    # Add/update the metadata to the primary HDU of these files.
    for fitsfile in output_files:
        eotestUtils.addHeaderData(fitsfile, LSST_NUM=sensor_id, TESTTYPE='FE55',
                                  DATE=eotestUtils.utc_now_isoformat(),
                                  CCD_MANU=ccd_vendor.upper())

    #
    # Persist the mean bias FITS file.
    #
    bias_mean_file = glob.glob('%(sensor_id)s_mean_bias_*.fits' % locals())[0]
    results.append(lcatr.schema.fileref.make(bias_mean_file))
    #
    # Common metadata for persisted non-FITS files.
    #
    md = siteUtils.DataCatalogMetadata(CCD_MANU=ccd_vendor.upper(),
                                       LSST_NUM=sensor_id,
                                       producer='SR-EOT-1',
                                       TESTTYPE='FE55',
                                       TEST_CATEGORY='EO')
    #
    # Persist various png files.
    #
    png_files = glob.glob('%(sensor_id)s_fe55*.png' % locals())
    png_filerefs = []
    for png_file in png_files:
        dp = eotestUtils.png_data_product(png_file, sensor_id)
        png_filerefs.append(lcatr.schema.fileref.make(png_file,
                                                      metadata=md(DATA_PRODUCT=dp)))
    results.extend(png_filerefs)

    data = sensorTest.EOTestResults(gain_file)
    amps = data['AMP']
    gain_data = data['GAIN']
    gain_errors = data['GAIN_ERROR']
    sigmas = data['PSF_SIGMA']
    for amp, gain_value, gain_error, sigma in zip(amps, gain_data, gain_errors,
                                                  sigmas):
        results.append(lcatr.schema.valid(lcatr.schema.get('fe55_raft_analysis'),
                                          amp=amp, gain=gain_value,
                                          gain_error=gain_error,
                                          psf_sigma=sigma,
                                          slot=slots[sensor_id],
                                          sensor_id=sensor_id))

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
