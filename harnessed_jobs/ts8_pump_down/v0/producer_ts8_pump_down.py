#!/usr/bin/env python
import os
import numpy as np
import matplotlib.pyplot as plt
from ccsTools import ccsProducer, CcsRaftSetup

# Check that CCS_PUMP_OUTLET is set.
os.environ['CCS_PUMP_OUTLET']

ccsProducer('ts8_pump_down', 'ccs_ts8_pump_down.py',
            ccs_setup_class=CcsRaftSetup)
