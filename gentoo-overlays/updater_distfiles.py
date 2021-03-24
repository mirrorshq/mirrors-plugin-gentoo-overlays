#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import os
import re
import time
import pathlib
import subprocess
import robust_layer
import mirrors.plugin


def main():
    msId = mirrors.plugin.params["id"]
    tmpDir = mirrors.plugin.params["temp-directory"]
    stateDir = mirrors.plugin.params["state-directory"]
    dataDir = mirrors.plugin.params["storage-file"]["data-directory"]
    overlayDir = os.path.join(stateDir, "overlay-data")
    overlayVcsType = mirrors.plugin.params["config"]["sync-type"]
    overlayUrl = mirrors.plugin.params["config"]["sync-uri"]

    print("Updater started:")
    print("    %s: (%s) %s" % (msId, overlayVcsType, overlayUrl))

    # overlay files
    print("Refresh overlay files:")
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

    print("Download distfiles:")

    # fakes config files
    reposDir = os.path.join(tmpDir, "repos.conf")
    os.mkdir(reposDir)
    _generateCfgReposFile(reposDir, msId, overlayDir, _Util.repoGetRepoName(overlayDir))

    # download overlay distfiles
    _Util.cmdExec("/usr/bin/emirrordist", "--mirror",
                  "--verbose",
                  "--ignore-default-opts",
                  "--config-root=%s" % (tmpDir),
                  "--repo=%s" % (msId),
                  "--distfiles=%s" % (dataDir),
                  "--delete")


def _generateCfgReposFile(dstDir, overlayName, overlayDir, innerRepoName):
    with open(os.path.join(dstDir, overlayName), "w") as f:
        buf = ""
        buf += "[%s]\n" % (innerRepoName)
        buf += "auto-sync = no\n"
        buf += "priority = 5000\n"
        buf += "location = %s\n" % (overlayDir)
        f.write(buf)


class _Util:

    @staticmethod
    def repoGetRepoName(repoDir):
        layoutFn = os.path.join(repoDir, "metadata", "layout.conf")
        if os.path.exists(layoutFn):
            m = re.search("repo-name = (\\S+)", pathlib.Path(layoutFn).read_text(), re.M)
            if m is not None:
                return m.group(1)

        repoNameFn = os.path.join(repoDir, "profiles", "repo_name")
        if os.path.exists(repoNameFn):
            ret = pathlib.Path(repoNameFn).read_text().rstrip("\n")
            ret = ret.replace(" ", "-")                         # it seems this translation is neccessary
            return ret

        # fatal error: can not get repoName
        return None

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
