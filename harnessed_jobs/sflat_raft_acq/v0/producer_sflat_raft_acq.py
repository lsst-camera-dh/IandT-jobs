#!/usr/bin/env python
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('sflat_raft_acq', 'ccs_sflat_raft_acq',
            ccs_setup_class=CcsRaftSetup)
