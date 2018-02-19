#!/usr/bin/env python
"""
Producer script for ts8_generic_acq harnessed job.
"""
import os
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('ts8_generic_acq', 'ccs_ts8_generic_acq.py',
            ccs_setup_class=CcsRaftSetup,
            sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),
                       os.path.join(os.environ['JHCCSUTILSDIR'], 'python')))
