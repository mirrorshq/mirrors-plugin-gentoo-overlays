#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import time
import subprocess
import robust_layer
import mirrors.plugin


def main():
    stateDir = mirrors.plugin.params["storage-file"]["state-directory"]
    dataDir = mirrors.plugin.params["storage-file"]["data-directory"]

    overlayDir = os.path.join(stateDir, "overlay-data")
    overlayVcsType = mirrors.plugin.params["config"]["sync-type"]
    overlayUrl = mirrors.plugin.params["config"]["sync-uri"]

    if overlayVcsType == "git":
        robust_layer.simple_git.pull(overlayDir, reclone_on_failure=True, url=overlayUrl)
    elif overlayVcsType == "svn":
        robust_layer.simple_subversion.update(overlayDir, recheckout_on_failure=True, url=overlayUrl)
    elif overlayVcsType == "mercurial":
        # FIXME
        assert False
    elif overlayVcsType == "rsync":
        # FIXME
        assert False
    else:
        assert False

    # download overlay distfiles
    _Util.cmdExec("/usr/bin/emirrordist", "--mirror",
                  "--verbose",
                  "--ignore-default-opts",
                  "--distfiles=%s" % (dataDir),
                  "--delete")


class _Util:

    @staticmethod
    def cmdExec(cmd, *kargs):
        # call command to execute frontend job
        #
        # scenario 1, process group receives SIGTERM, SIGINT and SIGHUP:
        #   * callee must auto-terminate, and cause no side-effect
        #   * caller must be terminate AFTER child-process, and do neccessary finalization
        #   * termination information should be printed by callee, not caller
        # scenario 2, caller receives SIGTERM, SIGINT, SIGHUP:
        #   * caller should terminate callee, wait callee to stop, do neccessary finalization, print termination information, and be terminated by signal
        #   * callee does not need to treat this scenario specially
        # scenario 3, callee receives SIGTERM, SIGINT, SIGHUP:
        #   * caller detects child-process failure and do appopriate treatment
        #   * callee should print termination information

        # FIXME, the above condition is not met, FmUtil.shellExec has the same problem

        ret = subprocess.run([cmd] + list(kargs), universal_newlines=True)
        if ret.returncode > 128:
            time.sleep(1.0)
        ret.check_returncode()


###############################################################################

if __name__ == "__main__":
    main()
