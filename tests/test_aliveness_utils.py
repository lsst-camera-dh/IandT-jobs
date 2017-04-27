"""
Test code for aliveness_utils module.
"""
import os
import unittest
import itertools
from numpy.random import permutation
import astropy.io.fits as fits
import lsst.eotest.sensor as sensorTest
from lsst.eotest.sensor.sim_tools import simulateFlat
import aliveness_utils

class AlivenessUtilsTestCase(unittest.TestCase):
    "Test case class for aliveness test utilities"
    def setUp(self):
        """
        Generate bias and flat to use for mixing channels for test
        images.
        """
        os.chdir(os.path.join(os.environ['IANDTJOBSDIR'], 'tests'))
        gain = 4.
        level = 4000.
        self.nominal_signal = level/gain

        self.bias_file = 'temp_bias.fits'
        simulateFlat(self.bias_file, level, gain, exptime=0, verbose=False)

        self.flat_file = 'temp_flat.fits'
        simulateFlat(self.flat_file, level, gain, exptime=1, verbose=False)
        self.raft_files = []
        self.slots = []
        self.nbad = {}

    def make_raft_files(self):
        """
        Make a collection of single sensor images, one for each slot
        in a raft, with a prescribed number of bad channels.
        """
        bias_frame = fits.open(self.bias_file)
        self.slots = ['S%i%i' % pair for pair in
                      itertools.product(range(3), range(3))]
        self.raft_files = [os.path.join(slot,
                                        '%s_sensor_frame.fits' % slot[-2:])
                           for slot in self.slots]
        for i, raft_file in enumerate(self.raft_files):
            slot = self.slots[i]
            if not os.path.isdir(slot):
                os.mkdir(os.path.join(slot))
            flat_frame = fits.open(self.flat_file)
            # Insert i+1 bad channels in random locations.
            num_bad = i + 1
            self.nbad[slot] = num_bad
            channels = permutation(range(1, 17))[:num_bad]
            for channel in channels:
                flat_frame[channel] = bias_frame[channel]
            flat_frame.writeto(raft_file, clobber=True)

    def tearDown(self):
        "Clean up FITS files"
        os.remove(self.bias_file)
        os.remove(self.flat_file)
        for item in self.raft_files:
            try:
                os.remove(item)
            except OSError:
                pass
        for item in self.slots:
            try:
                os.rmdir(item)
            except OSError:
                pass

    def test_get_median_signal_levels(self):
        """
        Test the get_median_signal_levels function on the flat and bias
        frames.
        """
        flat = sensorTest.MaskedCCD(self.flat_file)
        overscan = flat.amp_geom.serial_overscan
        imaging = flat.amp_geom.imaging
        imaging_signals \
            = aliveness_utils.get_median_signal_levels(flat, imaging)
        oscan_signals \
            = aliveness_utils.get_median_signal_levels(flat, overscan)
        for amp in oscan_signals:
            signal = imaging_signals[amp] - oscan_signals[amp]
            self.assertGreater(signal, 0.9*self.nominal_signal)
            self.assertLess(signal, 1.1*self.nominal_signal)

    def test_raft_channel_statuses(self):
        "Test the raft_channel_statuses function."
        self.make_raft_files()
        channel_status, exptime \
            = aliveness_utils.raft_channel_statuses(self.raft_files)[1:]
        self.assertAlmostEqual(exptime, 1.)
        for slot in channel_status:
            num_bad = len([x for x in channel_status[slot].values()
                           if x == 'bad'])
            self.assertEqual(num_bad, self.nbad[slot])

if __name__ == '__main__':
    unittest.main()
