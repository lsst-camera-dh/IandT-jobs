#!/usr/bin/env python
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('ts8_ready_acq', 'ccs_ts8_ready_acq.py',
            ccs_setup_class=CcsRaftSetup,
            sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),))
