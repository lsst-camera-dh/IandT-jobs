import os

def make_scripts(job_name, job_dir, clobber=False):
    with open(os.path.join(job_dir, 'modulefile'), 'w') as output:
        output.write("""#%%Module1.0 #-*-tcl-*-#
source "$::env(LCATR_MODULES)/lcatr.tcl"
lcatr_package producer_%(job_name)s.py validator_%(job_name)s.py
""" % locals())
    producer_script = os.path.join(job_dir,
                                   'producer_%(job_name)s.py' % locals())
    if clobber or not os.path.isfile(producer_script):
        with open(producer_script, 'w') as output:
            output.write('#!/usr/bin/env python\n')
    validator_script = os.path.join(job_dir,
                                    'validator_%(job_name)s.py' % locals())
    if clobber or not os.path.isfile(validator_script):
        with open(validator_script, 'w') as output:
            output.write('''#!/usr/bin/env python
import lcatr.schema

results = []

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
''')

execfile('simulation/TS8_sim_traveler.py')
harnessed_jobs = [x[0] for x in traveler_data]

rootdir = '/nfs/slac/g/ki/ki18/jchiang/LSST/lsst-camera-dh/IandT-jobs'
for job_name in harnessed_jobs:
    job_dir = os.path.join(rootdir, 'harnessed_jobs', job_name, 'v0')
    try:
        os.makedirs(job_dir)
    except OSError as eobj:
        pass
    make_scripts(job_name, job_dir)
