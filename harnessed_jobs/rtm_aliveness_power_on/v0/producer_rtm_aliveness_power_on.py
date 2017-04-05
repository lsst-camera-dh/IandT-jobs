#!/usr/bin/env python
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('rtm_aliveness_power_on', 'ccs_rtm_aliveness_power_on.py',
            ccs_setup_class=CcsRaftSetup)
