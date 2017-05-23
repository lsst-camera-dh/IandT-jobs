#!/usr/bin/env python
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
from ccsTools import ccsProducer, CcsRaftSetup

ccsProducer('ts8_preflight_acq', 'ccs_ts8_preflight_acq.py',
            ccs_setup_class=CcsRaftSetup,
            sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),))

# Create png files of photodiode current vs time.
pd_files = glob.glob('pd-values*.txt')
for pd_file in pd_files:
    pd_results = np.recfromtxt(pd_file, names=['time', 'current'])
    plt.plot(pd_results.time*1e-9, pd_results.current)
    plt.ylabel('Current (nA)')
    plt.xlabel('Time (s)')   #TODO: check time units.
    plt.savefig(pd_file.replace('.txt', '.png'))
