#!/usr/bin/env python
#from ccsTools import ccsValidator
import glob
import os
import lcatr.schema
import siteUtils

raft_id = siteUtils.getUnitId()

md = siteUtils.DataCatalogMetadata(LSST_NUM=raft_id,
                                   PRODUCER='INT-SR-MET-01',
                                   ORIGIN='SLAC',
                                   TEST_CATEGORY='MET')

# Find the scan plan file in the current working directory
scanplan = glob.glob("*scanplan*")[0]

# Find the scan data file
scandata = glob.glob("*data.txt")[0]

results = [lcatr.schema.fileref.make(scanplan, metadata=md(DATA_PRODUCT='MET_DATA')),
           lcatr.schema.fileref.make(scandata, metadata=md(DATA_PRODUCT='MET_DATA'))]

results.extend(siteUtils.jobInfo())
results.extend(siteUtils.packageVersions())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
