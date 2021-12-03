import os
import glob
import sys
import time

bot_data_folder = sys.argv[1]
#bot_data_folder = '/sdf/group/lsst/camera/IandT/rawData/focal-plane/20211201'

num_frames = len(glob.glob(os.path.join(bot_data_folder, '[MT][CS]_C_*')))

secs_per_frame = 21.
offset = 1.5*3600
duration = time.gmtime(secs_per_frame*num_frames + offset)
print(time.strftime('%H:%M:%S', duration))

