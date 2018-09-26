#!/usr/bin/env python
import os
import subprocess
jh_ccs_utils_path = os.path.join(os.environ['JHCCSUTILSDIR'], 'python')
ccs_script = os.path.join(os.environ['IANDTJOBSDIR'], 'harnessed_jobs',
                          'BOT_acq', 'v0', 'ccs_BOT_acq.py')
command = '/lsst/ccs/dev/bin/ccs-script {} {}'.format(ccs_script,
                                                      jh_ccs_utils_path)
subprocess.check_call(command, shell=True)
