from eTravelerComponents import Traveler

traveler = Traveler('TS8_sim', 'ScienceRaft', 'Test Stand 8 EO simulation')

#
# Data acquisition jobs
#
fe55_raft_acq = traveler.stepFactory('fe55_raft_acq',
                                     description='Fe55 acquisition')
dark_raft_acq = traveler.stepFactory('dark_raft_acq',
                                     description='Darks acquisition')
flat_pair_raft_acq = traveler.stepFactory('flat_pair_raft_acq',
                                          description='Flat pairs acquisition')
ppump_raft_acq = traveler.stepFactory('ppump_raft_acq',
                                      description='Pocket Pumping acquisition')
sflat_raft_acq = traveler.stepFactory('sflat_raft_acq',
                                      description='Superflats acquisition')
qe_raft_acq = traveler.stepFactory('qe_raft_acq', description='QE acquisition')
spot_raft_acq = traveler.stepFactory('spot_raft_acq',
                                     description='Spot acquisition')

#
# Analysis jobs
#
fe55_analysis = traveler.stepFactory('fe55_raft_analysis',
                                     description='Fe55 analysis')
fe55_analysis.add_pre_reqs(fe55_raft_acq)

read_noise = traveler.stepFactory('read_noise_raft',
                                  description='Read noise analysis')
read_noise.add_pre_reqs(fe55_raft_acq, fe55_analysis)

bright_defects = traveler.stepFactory('bright_defects_raft',
                                      description='Bright defects analysis')
bright_defects.add_pre_reqs(dark_raft_acq, fe55_analysis)

dark_defects = traveler.stepFactory('dark_defects_raft',
                                    description='Dark defects analysis')
dark_defects.add_pre_reqs(sflat_raft_acq, fe55_analysis, bright_defects)

traps = traveler.stepFactory('traps_raft', description='Charge traps analysis')
traps.add_pre_reqs(ppump_raft_acq, fe55_analysis, bright_defects, dark_defects)

mask_generators = fe55_analysis, bright_defects, dark_defects, traps

dark_current = traveler.stepFactory('dark_current_raft',
                                    description='Dark current analysis')
dark_current.add_pre_reqs(dark_raft_acq)
dark_current.add_pre_reqs(*mask_generators)

cte = traveler.stepFactory('cte_raft', description='Charge transfer efficiency')
cte.add_pre_reqs(sflat_raft_acq)
cte.add_pre_reqs(*mask_generators)

prnu = \
    traveler.stepFactory('prnu_raft',
                         description='Photo-response non-uniformity analysis')
prnu.add_pre_reqs(qe_raft_acq)
prnu.add_pre_reqs(*mask_generators)

flat_pairs_analysis = \
    traveler.stepFactory('flat_pairs_raft_analysis',
                         description='Full well and linearity analysis')
flat_pairs_analysis.add_pre_reqs(flat_pair_raft_acq)
flat_pairs_analysis.add_pre_reqs(*mask_generators)

ptc = traveler.stepFactory('ptc_raft', description='Photon transfer curve')
ptc.add_pre_reqs(flat_pair_raft_acq)
ptc.add_pre_reqs(*mask_generators)

qe_analysis = traveler.stepFactory('qe_raft_analysis', description='QE analysis')
qe_analysis.add_pre_reqs(qe_raft_acq)
qe_analysis.add_pre_reqs(*mask_generators)

crosstalk = traveler.stepFactory('crosstalk_raft',
                                 description='Crosstalk analysis')
crosstalk.add_pre_reqs(spot_raft_acq)
crosstalk.add_pre_reqs(*mask_generators)

test_report = traveler.stepFactory('test_report_raft',
                                   description='Test report generation')
test_report.add_pre_reqs(fe55_analysis, read_noise, bright_defects,
                         dark_defects, traps, dark_current, cte, prnu,
                         flat_pairs_analysis, ptc, qe_analysis, crosstalk)

#
# Write travelers
#
traveler.write_fake_eT_traveler('TS8_sim_traveler.py')
traveler.write_yml('TS8_sim_traveler.yml')
