#!/usr/bin/env python
import os
import numpy as np
import matplotlib.pyplot as plt
from ccsTools import ccsProducer, CcsRaftSetup

# Check that CCS_CRYO_OUTLET is set.
os.environ['CCS_CRYO_OUTLET']

ccsProducer('ts8_cool_down', 'ccs_ts8_cool_down.py',
            ccs_setup_class=CcsRaftSetup)
