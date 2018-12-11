#!/usr/bin/env python
"""
Validator script for BOT aliveness test acquisitions.
"""
import os
import glob
import lcatr.schema
import lsst.eotest.image_utils as imutils
import siteUtils
import camera_info
import aliveness_utils

job_schema = lcatr.schema.get('BOT_aliveness')

run_number = siteUtils.getRunNumber()

results = []

raft_names = camera_info.get_raft_names()
for raft_name in raft_names:
    pattern = 'dark_dark_*/*_{}_*.fits'.format(raft_name)
    fits_files = sorted(glob.glob(pattern))
    for fits_file in fits_files:
        results.append(lcatr.schema.fileref.make(fits_file))
    channel_signal, channel_status, exptime \
        = aliveness_utils.raft_channel_statuses(fits_files)
    for slot_name in channel_status:
        bad_channels = 0
        for amp, status in channel_status[slot_name].items():
            if channel_status[slot_name][amp] == 'bad':
                bad_channels += 1
                signal = channel_signal[slot_name][amp]
                channel = imutils.channelIds[amp]
        results.append(lcatr.schema.valid(job_schema,
                                          exptime=exptime,
                                          slot=slot_name,
                                          raft=raft_name))

# Add the png files.
md = siteUtils.DataCatalogMetadata(ORIGIN=siteUtils.getSiteName(),
                                   TEST_CATEGORY='EO')
results.extend(siteUtils.persist_png_files('*.png', raft_name, metadata=md))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
