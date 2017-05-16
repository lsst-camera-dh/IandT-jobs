#!/bin/bash
#
# These commands have been translated from
#
# https://github.com/lsst-camera-dh/harnessed-jobs/blob/master/T08/rebalive_power/v0/rebootrce.sh
#
# in order to be run on lsst-ir2daq01.
#
source /srv/nfs/lsst-daq/rpt-sdk/current/i86-linux-64/tools/envs-sdk.sh
cob_rce_reset 192.168.0.2/1/0/0
sleep 20
/srv/nfs/lsst-daq/daq-sdk/current/x86/bin/rms_servers
