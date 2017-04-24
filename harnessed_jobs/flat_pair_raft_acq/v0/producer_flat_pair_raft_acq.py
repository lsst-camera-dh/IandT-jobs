#!/usr/bin/env python
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('flat_pair_raft_acq', 'ccs_flat_pair_raft_acq',
            ccs_setup_class=CcsRaftSetup)
