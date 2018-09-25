#!/usr/bin/env python
import subprocess
command = '/lsst/ccs/dev/bin/ccs-script {}'.format('ccs_BOT_acq.py')
subprocess.check_call(command, shell=True)
