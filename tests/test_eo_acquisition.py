"""
Unit tests for eo_acquisition module.
"""
import os
import unittest
from eo_acquisition import *

acq_config_file = os.path.join(os.environ['IANDTJOBSDIR'], 'tests',
                               'eo_acq_config.txt')
class EOAcqConfigTestCase(unittest.TestCase):
    "TestCase class for the EOAcqConfig class."
    def test_eo_acq_config(self):
        "Test that the acq config file is correctly parsed."
        eo_config = EOAcqConfig(acq_config_file)
        self.assertEqual(eo_config['FE55_BCOUNT'], '25')
        self.assertEqual(eo_config['FLAT_HILIM'], '240.0')
        self.assertEqual(eo_config['FLAT_LOLIM'], '0.025')

class EOAcquisitionTestCase(unittest.TestCase):
    "TestCase class for the EOAcquisition class."
    def test_instructions(self):
        "Test that the acquisition instructions are correctly parsed."
        metadata = AcqMetadata(cwd='.', raft_id="my_raft", run_number="my_run")
        test_type = "FLAT"
        acq = EOAcquisition("seqfile.txt", acq_config_file, test_type, metadata)
        self.assertEqual(acq.md.cwd, '.')
        self.assertEqual(acq.md.raft_id, 'my_raft')
        self.assertEqual(len(acq.instructions), 21)
        self.assertAlmostEqual(acq.exptime_min, 0.025)
        self.assertAlmostEqual(acq.exptime_max, 240.)
        self.assertAlmostEqual(acq.wl, 675.)
        self.assertEqual(acq.test_type, test_type)
        self.assertRaises(NotImplementedError, acq.run)

    def test_constructor(self):
        "Test the EOAcquisition construction."
        metadata = AcqMetadata(cwd='.', raft_id="my_raft", run_number="my_run")
        test_type = "FLAT"
        subsystems = dict(ts8="ts8")
        self.assertRaises(RuntimeError, EOAcquisition,
                          "seqfile.txt", acq_config_file, test_type, metadata,
                          subsystems=subsystems)

if __name__ == '__main__':
    unittest.main()
