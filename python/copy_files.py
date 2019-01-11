import os

def copy_files(files, dest, copyfunc=os.symlink):
    if not os.path.isdir(dest):
        raise RuntimeError("directory {} does not exist".format(dest))
    for item in files:
        copyfunc(item, os.path.join(dest, os.path.basename(item)))
