#!/usr/bin/env python
import os
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('rtm_aliveness_power_on', 'ccs_rtm_aliveness_power_on.py',
            ccs_setup_class=CcsRaftSetup,
            sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),))
