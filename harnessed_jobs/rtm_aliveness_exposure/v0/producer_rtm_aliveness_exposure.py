#!/usr/bin/env python
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('rtm_aliveness_exposure', 'ccs_rtm_aliveness_exposure.py',
            ccs_setup_class=CcsRaftSetup)
