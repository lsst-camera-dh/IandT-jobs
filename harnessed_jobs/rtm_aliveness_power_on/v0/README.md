This job loops over the REBs in a raft and executes the power-on sequence
described in LCA-10064-A (available only in draft form at the time of this
writing).

### `ccs_rtm_aliveness_power_on.py`

For each REB, perform the following steps:

* Execute the REB power-supply subsystem command `sequencePower <line> True`.
  (section 10.4.2.2, step 2)

* Immediately check that all of the REB P/S currents are within the
  limits in table 9 in section 14.2.  (section 10.4.2.2, step 3)

* Wait 15 seconds for the FPGA to boot.

* Check again that all of the REB P/S currents are within the
  limits in table 9 in section 14.2.  (section 10.4.2.2, step 4)

* Read the register 1 of the REB to verify the data link.
  (section 10.4.2.2, step 5)

* Read the REB info via the CCS commands `getREBHwVersions` and
  `getREBSerialNumbers`.  Compare the REB serial number with serial
  number for that REB from the eTraveler tables.  If they disagree,
  raise an exception.  This will fail the harnessed job.
  (section 10.4.2.2, step 6)

* Print the firmware version, obtained by CCS, to the terminal window.
  There is no way of getting the intended firmware via software so the
  operator will need to check this manually.  (section 10.4.2.2, step 7)

* Compare the REB P/S currents with the values read for the REBs via
  the teststand subsystem.  If any values lie outside of the
  comparative range in table 9 in section 14.2, raise an exception
  that will fail the job.  (section 10.4.2.2, step 8)

* NB: all voltages and currents are assumed to be monitored in the CCS
  trending tables.  Any display of trending quantities area assumed to
  be available from the CCS console. (section 10.4.2.2, steps 9 and 10).

* Load the sensor-specific configurations via
  ```
  loadCategories Rafts:<sensor_type>
  loadCategories RaftLimits:<sensor_type>
  ```
  where `<sensor_type>` is `itl` or `e2v`.

* Execute the `powerOn <REB id>` CCS command, and write the output
  to a text file that will be persisted by the eTraveler.
  (section 10.4.2.2, steps 11 through 13)

### `producer_rtm_aliveness_power_on.py`

* This is a python script for the JH code to execute that runs
  the above `ccs_rtm_aliveness_power_on.py` jython script via the
  [`harnessed-jobs/python/ccsTools.py`](https://github.com/lsst-camera-dh/harnessed-jobs/blob/master/python/ccsTools.py) interface.

### `validator_rtm_aliveness_power_on.py`

* Make trending plots for the channels listed
  `rtm_aliveness_power_on.cfg`.

* Persist the `.png` and `.txt` files with those trending data via
  the JH/eT mechanism.
