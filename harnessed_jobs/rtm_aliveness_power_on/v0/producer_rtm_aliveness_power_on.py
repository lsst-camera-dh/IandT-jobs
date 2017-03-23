#!/usr/bin/env python
from ccsTools import ccsProducer
import subprocess

subprocess.check_call('chmod -R o+w /home/jchiang/work/jh_stage', shell=True)
subprocess.check_call('chmod -R o+w /home/jchiang/work/jh_archive', shell=True)

ccsProducer('rtm_aliveness_power_on', 'ccs_rtm_aliveness_power_on.py')
