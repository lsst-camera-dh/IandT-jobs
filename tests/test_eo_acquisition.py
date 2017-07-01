"""
Unit tests for eo_acquisition module.
"""
import os
from collections import namedtuple
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
    def setUp(self):
        SensorInfo = namedtuple('SensorInfo',
                                'sensor_id manufacturer_sn'.split())
        self.ccd_names = dict()
        self.ccd_names["S00"] = SensorInfo("ITL-3800C-023-Dev", "19186")
        self.ccd_names["S01"] = SensorInfo("ITL-3800C-032", "19171")
        self.ccd_names["S02"] = SensorInfo("ITL-3800C-042", "19269")
        self.ccd_names["S10"] = SensorInfo("ITL-3800C-090-Dev", "20204")
        self.ccd_names["S11"] = SensorInfo("ITL-3800C-107", "20070")
        self.ccd_names["S12"] = SensorInfo("ITL-3800C-007", "20235")
        self.ccd_names["S20"] = SensorInfo("ITL-3800C-004", "20375")
        self.ccd_names["S21"] = SensorInfo("ITL-3800C-139-Dev", "20275")
        self.ccd_names["S22"] = SensorInfo("ITL-3800C-013-Dev", "20289")

    def test_instructions(self):
        "Test that the acquisition instructions are correctly parsed."
        metadata = AcqMetadata(cwd='.', raft_id="my_raft", run_number="my_run")
        test_type = "FLAT"
        subsystems = dict(ts8="ts8-proxy", pd='subsystem-proxy',
                          mono='subsystem-proxy', rebps='subsystem-proxy')
        acq = EOAcquisition("seqfile.txt", acq_config_file, test_type, metadata,
                            subsystems, self.ccd_names)
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
        subsystems = dict(ts8="ts8-proxy", pd='subsystem-proxy')
        self.assertRaises(RuntimeError, EOAcquisition,
                          "seqfile.txt", acq_config_file, test_type, metadata,
                          subsystems, self.ccd_names)

if __name__ == '__main__':
    unittest.main()
