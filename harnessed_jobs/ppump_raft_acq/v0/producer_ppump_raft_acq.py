#!/usr/bin/env python
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('ppump_raft_acq', 'ccs_ppump_raft_acq',
            ccs_setup_class=CcsRaftSetup)
