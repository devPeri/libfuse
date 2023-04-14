import os
import sys
import subprocess
import tempfile
from util import (pjoin, basename, base_cmdline, wait_for_mount, cleanup, umount)


# ###
# ### test case for Issue #746
# ###
#
# If RELEASE and UNLINK opcodes are sent back to back, and fuse_fs_release()
# and fuse_fs_rename() are slow to execute, UNLINK will run while RELEASE is
# still executing, UNLINK will try to rename the file, and while the rename
# is happening the RELEASE will finish executing. So at the end, RELEASE will
# not detect in time that UNLINK has happened, and UNLINK will not detect in
# time that RELEASE has happened.
#
# NOTE: This is triggered only when nullpath_ok is set.
#
# If it is not SET then get_path_nullok() called by fuse_lib_release() will
# call get_path_common() and lock the path, and then the fuse_lib_unlink()
# will wait for the path to be unlocked before executing and thus synchronise
# with fuse_lib_release().
#
# If it is SET then get_path_nullok() will just set the path to null and
# return without locking anything and thus allowing fuse_lib_unlink() to
# eventually execute unimpeded while fuse_lib_release() is still running.

## Normal run:
# python3 test746.py
#
## Disable release() & rename() runtime delay injection:
# TEST746_DELAY_DISABLE=1 python3 test746.py


# set the path for the library to preload
preloadLib = base_cmdline + \
    [ pjoin(basename, "test", "test746.so") ]
preloadLib = preloadLib[0]
print("preloadLib: ", preloadLib)

# create the FUSE mountpoint
fuseMNT = "/tmp/test746"
print("fuseMNT: ", fuseMNT)
os.makedirs(fuseMNT, exist_ok=True)

# set the FUSE binary path
fuseCMD = base_cmdline + \
    [ pjoin(basename, 'example', 'passthrough_fh'),
    "-f", fuseMNT]
print("fuseCMD: ", str(fuseCMD))

# start FUSE with out preload library
os.environ["LD_PRELOAD"] = preloadLib
fuseProcess = subprocess.Popen(fuseCMD, shell = False)
os.environ["LD_PRELOAD"] = ""

ret = -1
try:
    wait_for_mount(fuseProcess, fuseMNT)

    # use TemporaryDirectory so that it gets cleaned up at the end automatically
    tempDir = tempfile.TemporaryDirectory(dir=fuseMNT + "/tmp/")
    tempDirPath = tempDir.name
    #print("tempDir: " + tempDirPath);

    tempFile, tempFilePath = tempfile.mkstemp(dir=tempDir.name)
    #print("tempFile: " + tempFilePath);

    # test for the race condition
    os.close(tempFile)
    os.unlink(tempFilePath)

    # check if any leftover files are still there
    tempDirFiles = os.listdir(tempDirPath)
    #print(tempDirFiles)

    if len(tempDirFiles) == 0:
        print(" *** TEST746 PASS ***")
        ret = 0
    else:
        print(" *** TEST746 FAIL ***")
        ret = 1

except:
    cleanup(fuseProcess, fuseMNT)

else:
    umount(fuseProcess, fuseMNT)

os.removedirs(fuseMNT);

sys.exit(ret)