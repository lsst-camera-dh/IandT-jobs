#!/usr/bin/env python
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('qe_raft_acq', 'ccs_qe_raft_acq', ccs_setup_class=CcsRaftSetup)
