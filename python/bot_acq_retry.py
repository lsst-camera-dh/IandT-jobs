import os
import shutil
import glob

def copy_exposure_symlinks(copy_links=True):
    """
    If the current job execution is a retry, there will be a previous
    working directory with symlinks to the successful BOT exposures.
    This function finds the last working directory by sorting on the
    activityId directory names, copies the exposure symlinks to the
    current directory and returns the number of symlinks it made.

    If there is no previous working directory, zero is returned.
    """
    current_dir = os.path.abspath('.').split('/')[-1]
    try:
        last_dir = sorted([_ for _ in glob.glob('../*')
                           if current_dir not in _])[-1]
    except IndexError:
        return 0

    num_symlinks = 0
    for item in glob.glob(os.path.join(last_dir, '*_[0-9]*')):
        if os.path.islink(item):
            exposure_name = os.path.basename(item)
            num_symlinks += 1
            if copy_links and not os.path.islink(exposure_name):
                shutil.copy(item, exposure_name, follow_symlinks=False)
    return num_symlinks
