#!/usr/bin/env python
import os
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('sflat_raft_acq', 'ccs_sflat_raft_acq.py',
            ccs_setup_class=CcsRaftSetup,
            sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),))
