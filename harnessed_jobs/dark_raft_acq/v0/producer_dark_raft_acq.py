#!/usr/bin/env python
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('dark_raft_acq', 'ccs_dark_raft_acq', ccs_setup_class=CcsRaftSetup)
