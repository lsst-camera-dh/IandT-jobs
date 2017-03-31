#!/usr/bin/env python
import glob
import lcatr.schema
import lsst.eotest.image_utils as imutils
import siteUtils
import aliveness_utils

results = []

job_schema = lcatr.schema.get('rtm_aliveness_exposure')

image_types = 'bias flat fe55'.split()

row_template = "%(image_type)s  %(slot)s  %(channel)s  %(signal)s  %(status)s\n"

outfile = '%s_%s_rtm_aliveness_bad_channels.txt' % (siteUtils.getUnitId(),
                                                    siteUtils.getRunNumber())
with open(outfile, 'w') as output:
    for image_type in image_types:
        fits_files = sorted(glob.glob('*_%s_*.fits' % image_type))
        channel_signal, channel_status, exptime \
            = aliveness_utils.raft_channel_statuses(fits_files)
        for slot in channel_status:
            bad_channels = 0
            for amp, status in channel_status[slot].items():
                if channel_status[slot][amp] == 'bad':
                    bad_channels += 1
                    signal = channel_signal[slot][amp]
                    channel = imutils.channelIds[amp]
                    output.write(row_template % locals())
            results.append(lcatr.schema.valid(job_schema,
                                              image_type=image_type,
                                              exptime=exptime,
                                              slot=slot,
                                              bad_channels=bad_channels))

results.append(lcatr.schema.fileref.make(outfile))
results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
