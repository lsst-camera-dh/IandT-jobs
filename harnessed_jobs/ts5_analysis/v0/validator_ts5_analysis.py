#!/usr/bin/env python
import lcatr.schema
import siteUtils
import numpy as np

producer = 'INT-SR-MET-01'

# Locate the output files from the producer step
# Read and parse the ASCII tables, registering extracted results with the eTraveler database
# Register the ASCII files and PNG plots with the eTraveler database/Data Catalog - including associated
# metadata
# Fill two schemas for the different TESTTYPE values

#testtype = 'FLATNESS'

raft_id = siteUtils.getUnitID()

md = siteUtils.DataCatalogMetadata(CCD_MANU=siteUtils.getCcdVendor(),
                                  LSST_NUM=raft_id,
                                  PRODUCER='INT-SR-MET-01',
                                  ORIGIN='SLAC',
                                  TEST_CATEGORY='MET')

results_file = glob.glob("*__ms.tnt")[0]
results = [lcatr.schema.fileref.make(results_file,
                                     metadata=md(DATA_PRODUCT='MET'))]

# Pick up and register all of the PNG files
png_files = glob.glob('*.png')
results.extend([lcatr.schema.fileref.make(item,
                                           metadata=md(DATA_PRODUCT='MET')
                for item in png_files])

# Parse the metadata from the scan file (also just notional)
temp_cryo = []
temp_reb0 = []
temp_reb1 = []
temp_reb2 = []

for line in open(raftData.infile):
    if line.startswith('# start time ='):
        tokens = line.split()
        start_time = float(tokens[4])
        end_time = float(tokens[9])
    if not line.startswith('#'):
        tokens = line.split()
        temp_cryo.append(float(tokens[6]))
        temp_reb0.append(float(tokens[7]))
        temp_reb1.append(float(tokens[8]))
        temp_reb2.append(float(tokens[9]))

temp_cryo_start = temp_cryo[0]
temp_cryo_end = temp_cryo[-1]
temp_cryo_avg = np.mean(temp_cryo)

temp_reb0_start = temp_reb0[0]
temp_reb0_end = temp_reb0[-1]
temp_reb0_avg = np.mean(temp_reb0)

temp_reb1_start = temp_reb1[0]
temp_reb1_end = temp_reb1[-1]
temp_reb1_avg = np.mean(temp_reb1)

temp_reb2_start = temp_reb2[0]
temp_reb2_end = temp_reb2[-1]
temp_reb2_avg = np.mean(temp_reb2)

# Also extract starting and ending time for the scan
start_time = 0
end_time = 100  # placeholders

# Read analysis results for the eTraveler database
datfile = glob.glob('*sensor-flatness_histogram_results')[0]
sensorflatness_quantile = []
sensorflatness_z = []
for line in open(datfile.infile):
    if line.startswith('QUANTILE'):
        tokens = line.split()
	sensorflatness_quantile.append(tokens[1])
	sensorflatness_z.append(tokens[2])

    if line.startswith('WIDTH  95%'):
        tokens = line.split()
        sensorflatness_pv_95 = float(tokens[2])
    if line.startswith('WIDTH 100%'):
        tokens = line.split()
        sensorflatness_pv_100 = float(tokens[2])

sensorflatness_dict = dict(zip(sensorflatness_quantile, sensorflatness_z))
sensorflatness_025 = sensorflatness_dict['0.0250']
sensorflatness_975 = sensorflatness_dict['0.9750']

datfile = glob.glob('*raft-flatness_histogram_results')[0]
flatness_quantile = []
flatness_z = []
for line in open(datfile.infile):
    if line.startswith('QUANTILE'):
        tokens = line.split()
	flatness_quantile.append(tokens[1])
	flatness_z.append(tokens[2])

    if line.startswith('WIDTH  95%'):
        tokens = line.split()
        flatness_pv_95 = float(tokens[2])
    if line.startswith('WIDTH 100%'):
        tokens = line.split()
        flatness_pv_100 = float(tokens[2])

flatness_dict = dict(zip(flatness_quantile, flatness_z))
flatness_025 = flatness_dict['0.0250']
flatness_975 = flatness_dict['0.9750']

datfile = glob.glob('*raft-imageheight_histogram_results')[0]
absheight_quantile = []
absheight_z = []
for line in open(datfile.infile):
    if line.startswith('QUANTILE'):
        tokens = line.split()
	absheight_quantile.append(tokens[1])
	absheight_z.append(tokens[2])

    if line.startswith('WIDTH  95%'):
        tokens = line.split()
        absheight_pv_95 = float(tokens[2])
    if line.startswith('WIDTH 100%'):
        tokens = line.split()
        absheight_pv_100 = float(tokens[2])

absheight_dict = dict(zip(absheight_quantile, absheight_z))
absheight_025 = absheight_dict['0.0250']
absheight_975 = absheight_dict['0.9750']

results.append(lcatr.schema.valid(lcatr.schema.get('ts5_conditions'),
                                  start_time=start_time,
                                  end_time=end_time,
                                  temp_cryo_start = temp_cryo[0],
                                  temp_reb0_start = temp_reb0[0],
                                  temp_reb1_start = temp_reb1[0],
                                  temp_reb2_start = temp_reb2[0],
                                  temp_cryo_end = temp_cryo[-1],
                                  temp_reb0_end = temp_reb0[-1],
                                  temp_reb1_end = temp_reb1[-1],
                                  temp_reb2_end = temp_reb2[-1]
				  temp_cryo_avg = np.mean(temp_cryo)
				  temp_reb0_avg = np.mean(temp_reb0)
				  temp_reb1_avg = np.mean(temp_reb1)
				  temp_reb2_avg = np.mean(temp_reb2)))

results.append(lcatr.schema.valid(lcatr.schema.get('ts5_flatness'),
				  flatness_025 = flatness_025,
				  flatness_975 = flatness_975,
				  flatness_pv_95 = flatness_pv_95,
				  flatness_pv_100 = flatness_pv_100,
				  flatness_quantile = flatness_quantile,
				  flatness_z = flatness_z))

results.append(lcatr.schema.valid(lcatr.schema.get('ts5_sensorflatness'),
				  sensorflatness_025 = sensorflatness_025,
				  sensorflatness_975 = sensorflatness_975,
				  sensorflatness_pv_95 = sensorflatness_pv_95,
				  sensorflatness_pv_100 = sensorflatness_pv_100,
				  sensorflatness_quantile = sensorflatness_quantile,
				  sensorflatness_z = sensorflatness_z))

results.append(lcatr.schema.valid(lcatr.schema.get('ts5_absheight'),
				  absheight_025 = absheight_025,
				  absheight_975 = absheight_975,
				  absheight_pv_95 = absheight_pv_95,
				  absheight_pv_100 = absheight_pv_100,
				  absheight_quantile = absheight_quantile,
				  absheight_z = absheight_z))
results.extend(siteUtils.jobInfo())
results.extend(siteUtils.packageVersions())

lcatr.schema.write_file(results)
lcatr.schema.validate_file()
