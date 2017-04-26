"""
Utilities to work with the ts8 subsystem.
"""

def set_ccd_info(ccs_sub, ccd_names):
    """
    Set the CCD serial numbers in the CCS code.  Get the CCD
    temperature and BSS voltages from the ts8 and ccs-rebps
    subsystems, and set those values in the CCS code.

    Parameters
    ----------
    ccs_sub : CcsSubsystems
        Container of CCS subsystems.
    ccd_names : dict
        Dictionary of namedtuple containing the CCD .sensor_id and
        .maufacturer_sn information, keyed by slot name.

    Notes
    -----
    This is function is a refactored version of
    harnessed-jobs/python/eolib.EOTS8SetupCCDInfo.
    """
    # Parse the printGeometry output to map CCD values to REBs.
    geo = ccs_sub.ts8.synchCommand(2, "printGeometry 3").getResult()
    for line in geo.split('\n'):
        if 'Sen' not in line:
            continue
        slot = 'S%s' % line[-2:]
        ccd_id = line.split(' ')[1]
        sensor = ccd_names[slot]

        # Set the LSST serial number.
        command = 'setLsstSerialNumber %s %s' % (ccd_id, sensor.sensor_id)
        ccs_sub.ts8.synchCommand(2, command)

        # Set the manufacturer serial number.
        command = ('setManufacturerSerialNumber %s %s'
                   % (ccd_id, sensor.manufacturer_sn))
        ccs_sub.ts8.synchCommand(command)

        # Set the CCD temperature.
        reb_id = int(slot[1])
        ccd_num = int(slot[2])
        command = "getChannelValue R00.Reb%d.CCDTemp%d" % (reb_id, ccd_num)
        ccdtemp = ccs_sub.ts8.synchCommand(2, command).getResult()
        command = "setMeasuredCCDTemperature %s %s" % (ccd_id, ccdtemp)
        ccs_sub.ts8.synchCommand(10, command)

        # Set the BSS voltage.
        command = "getChannelValue REB%s.hvbias.VbefSwch"  % reb_id
        hv = ccs_sub.rebps.synchCommand(10, command).getResult()
        command = "setMeasuredCCDBSS %s %s" % (ccd_id, hv)
        ccs_sub.ts8.synchCommand(10, command)
