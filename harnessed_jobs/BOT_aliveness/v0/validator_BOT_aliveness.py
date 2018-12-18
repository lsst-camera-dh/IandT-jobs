#!/usr/bin/env python
"""
Validator script for BOT aliveness test acquisitions.
"""
import os
import glob
import lcatr.schema
import lsst.eotest.image_utils as imutils
import siteUtils
from camera_components import camera_info
import aliveness_utils

job_schema = lcatr.schema.get('BOT_aliveness')

run_number = siteUtils.getRunNumber()

results = []

raft_names = camera_info.get_raft_names()
dark_frames = glob.glob('dark_dark_*')
row_template \
    = "%(exptime)s  %(slot_name)s  %(channel)s  %(signal)s  %(status)s\n"
for raft_name in raft_names:
    file_prefix = '{}_{}'.format(run_number, raft_name)
    bad_channel_entries = []
    for dark_frame in dark_frames:
        pattern = '{}/*_{}_*.fits'.format(dark_frame, raft_name)
        fits_files = sorted(glob.glob(pattern))
        if not fits_files:
            continue
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
                    bad_channel_entries.append(row_template % locals())
            results.append(lcatr.schema.valid(job_schema,
                                              exptime=exptime,
                                              slot=slot_name,
                                              raft=raft_name,
                                              bad_channels=bad_channels))
    if bad_channel_entries:
        outfile = '{}_BOT_aliveness_bad_channels.txt'.format(file_prefix)
        with open(outfile, 'w') as output:
            for line in bad_channel_entries:
                output.write(line)
        results.append(lcatr.schema.fileref.make(outfile))

# Add the png files.
md = siteUtils.DataCatalogMetadata(ORIGIN=siteUtils.getSiteName(),
                                   TEST_CATEGORY='EO')
results.extend(siteUtils.persist_png_files('*.png', raft_name, metadata=md))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
