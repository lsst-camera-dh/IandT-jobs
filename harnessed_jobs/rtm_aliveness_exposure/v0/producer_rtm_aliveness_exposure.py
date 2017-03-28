#!/usr/bin/env python
import ccsTools
import subprocess

print ccsTools.__file__
ccsTools.ccsProducer('rtm_aliveness_exposure', 'ccs_rtm_aliveness_exposure.py')
