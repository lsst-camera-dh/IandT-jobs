#!/usr/bin/env python
"""
Validator script for rtm_aliveness_exposure job.
"""
import glob
import lcatr.schema
import lsst.eotest.image_utils as imutils
import siteUtils
import aliveness_utils

results = []

job_schema = lcatr.schema.get('rtm_aliveness_exposure')

seqnos = '0100 1000 4000'.split()

row_template = "%(seqno)s  %(slot)s  %(channel)s  %(signal)s  %(status)s\n"

outfile = '%s_%s_rtm_aliveness_bad_channels.txt' % (siteUtils.getUnitId(),
                                                    siteUtils.getRunNumber())
with open(outfile, 'w') as output:
    for seqno in seqnos:
        fits_files = sorted(glob.glob('*_%s_*.fits' % seqno))
        for fits_file in fits_files:
            results.append(lcatr.schema.fileref.make(fits_file))
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
                                              exptime=exptime,
                                              slot=slot,
                                              bad_channels=bad_channels))

results.append(lcatr.schema.fileref.make(outfile))

# Persist the sequencer file that was used.
seq_file = glob.glob('*.seq')[0]
results.append(lcatr.schema.fileref.make(seq_file))

results.extend(siteUtils.jobInfo())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
