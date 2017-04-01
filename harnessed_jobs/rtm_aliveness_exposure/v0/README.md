This job produces a series of test exposures and measures the signal
levels for each segment to check for bad channels.

### `ccs_rtm_aliveness_exposure.py`

* Connect to the ts8 subsystem.

* Verify that the three expected REB devices are available.

* Set the output directory to the Job Harness staging area.

* Load the sequencer file.

  * `sequence_file` is set in the `acq.cfg` file ([BNL version](https://github.com/lsst-camera-dh/harnessed-jobs/blob/master/config/BNL/acq.cfg))

  * Take a "zero" second exposure.

* Take "bias", "flat", "fe55" exposures with `exptimes` 100, 1000, 4000 ms.

  * Set `test_type`, `image_type` values for header keywords

  * Set monochromator open-shutter and XED actuator flags.

### `producer_rtm_aliveness_power_on.py`

* This is a python script for the JH code to execute that runs
  the above `ccs_rtm_aliveness_exposure.py` jython script via the
  [`harnessed-jobs/python/ccsTools.py`](https://github.com/lsst-camera-dh/harnessed-jobs/blob/master/python/ccsTools.py) interface.

### `validator_rtm_aliveness_exposure.py`

* For each of the three image types/exposure times, loop over single
  sensor images for each of the 9 CCDs:

  * Compute median signal in imaging and overscan regions
    to obtain bias-subtracted signal for each channel using
    [code](https://github.com/lsst-camera-dh/IandT-jobs/blob/344feeaef58ccf03c27ce9c889e69fc87056c684/python/aliveness_utils.py) adapted from [Paul's connectivity script](https://github.com/lsst-camera-dh/harnessed-jobs/blob/master/T08/rebalive_exposure/v0/connectivityCheck.py).

  * Persist bad channel statistics to eTraveler results table.

* Write out results for all bad channels.

