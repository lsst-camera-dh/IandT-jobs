#!/usr/bin/env python
import os
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('flat_pair_raft_acq', 'ccs_flat_pair_raft_acq.py',
            ccs_setup_class=CcsRaftSetup,
            sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),))
