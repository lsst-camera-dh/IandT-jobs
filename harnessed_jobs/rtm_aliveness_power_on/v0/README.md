This job powers on each of the REBs and checks the that the currents
are within limits.

* `ccs_rtm_aliveness_power_on.py`

 * Define the channels to be checked for each REB and their limits (in mA).

 * Attach the CCS subsystems `ts8` and `ccs-rebps` (REB power-supply).

 * Map each REB to the corresponding power-line by powering on the
   `digital` and `analog` channel for one power-line at a time and
   looping over the unmapped REBs, reading the address 1 register to
   ascertain the connection.  This is based on [Homer's rebalive_handshake](https://github.com/lsst-camera-dh/harnessed-jobs/blob/master/T08/rebalive_handshake/v0/ccseorebalive_handshake.py) job.

 * Set the ts8 monitoring interval to 0.1s so that the trending plots
   have the desired resolution.

 * Loop over REBs
   * Power on each channel in order, checking currents for clockhi, clocklo,
     and od.
   * If a current is out of range, power down that channel and abort.
   * If a current measured by the ccs-rebps subsystem differs from the
     ts8 current by more than 10% issue a warning.

 * Load sensor-specific configurations

 * Turn on all clock and rail voltages for all REBs.

 * Restore the monitoring interval to 10s.

* `validator_rtm_aliveness_power_on.py`

  * Make trending plots for the channels listed `rtm_aliveness_power_on.cfg`.

  * Persist the .png and .txt files with those trending data via the
    JH/eT mechanism.
