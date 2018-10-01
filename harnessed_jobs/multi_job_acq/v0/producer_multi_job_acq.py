#!/usr/bin/env python
import os
from ccsTools import ccsProducer, CcsRaftSetup
from eo_acquisition import EOAcqConfig

# Mapping of acquisition type to harnessed job names. Commented out
# entries do not yet have harnessed jobs implemented.
job_names = {
    'bias': 'bias_raft_acq',
    'fe55': 'fe55_raft_acq',
    'dark': 'dark_raft_acq',
    'persistence': 'persistence_raft_acq',
    'sflat': 'sflat_raft_acq',
    'lambda': 'qe_raft_acq',
    'flat': 'flat_raft_acq',
    'scan': 'scan_mode_acq',
    'ppump': 'ppump_raft_acq'
    }

# Find the raft-level EO configuration file.
acq_config_file = os.path.join(os.environ['LCATR_CONFIG_DIR'], 'acq.cfg')
with open(acq_config_file, 'r') as acq_config:
    for line in acq_config:
        if line.startswith('rtmacqcfgfile'):
            eo_acq_config_file = line.split('=')[1].strip()

# Read in the acquisition sequence.
with open(eo_acq_config_file, 'r') as eo_acq:
    acqs = [x.split('#')[0].split()[1] for x in eo_acq
            if x.startswith('ACQUIRE')]

# Loop over the acquisition sequence, running the jython script
# associated with the single acquisition harnessed jobs.
for acq in acqs:
    try:
        job_name = job_names[acq]
    except KeyError:
        # harnessed job does not exist so skip.
        continue
    ccs_script = 'ccs_{}.py'.format(job_name)
    ccsProducer(job_name, ccs_script,
                ccs_setup_class=CcsRaftSetup,
                sys_paths=(os.path.join(os.environ['IANDTJOBSDIR'], 'python'),))
