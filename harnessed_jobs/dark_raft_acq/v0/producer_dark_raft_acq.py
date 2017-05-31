#!/usr/bin/env python
import os
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('dark_raft_acq', 'ccs_dark_raft_acq.py',
            ccs_setup_class=CcsRaftSetup,
            sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),))
