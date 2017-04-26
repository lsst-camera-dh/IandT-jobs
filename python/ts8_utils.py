import camera_components

def set_ccd_info(ccs_sub, raft_id):
    """
    Refactored version of eolib.EOTS8SetupCCDInfo
    """
    # Get the CCD information for the specified raft.
    raft = camera_components.Raft.create_from_etrav(raft_id)

    # Parse the printGeometry output to map CCD values to REBs.
    geo = ccs_sub.ts8.synchCommand(2, "printGeometry 3").getResult()
    for line in geo.split('\n'):
        if 'Sen' not in line:
            continue
        slot = 'S%s' % line[-2:]
        ccd_id = line.split(' ')[1]
        sensor = raft.sensor(slot)

        # Set the LSST serial number.
        command = 'setLsstSerialNumber %s %s' % (ccd_id, sensor.sensor_id)
        ccs_sub.ts8.synchCommand(2, command)

        # Set the manufacturer serial number.
        command = ('setManufacturerSerialNumber %s %s'
                   % (ccd_id, sensor.manufacturer_sn))
        ccs_sub.ts8.synchCommand(command)

        # Set the CCD temperature.
        rebid = int(slot[1])
        ccd_num = int(slot[2])
        command = "getChannelValue R00.Reb%i.CCDTemp%i" % (rebid, ccd_num)
        ccdtemp = ccs_sub.ts8.synchCommand(2, command).getResult()
        command = "setMeasuredCCDTemperature %s %s" % (ccd_id, ccdtemp)
        ccs_sub.ts8.synchCommand(10, command)

        # Set the BSS voltage.
        command = "getChannelValue REB%s.hvbias.VbefSwch"  % rebid
        hv = ccs_sub.rebps.synchCommand(10, command).getResult()
        command = "setMeasuredCCDBSS %s %s" % (ccd_id, hv)
        ccs_sub.ts8.synchCommand(10, command)
