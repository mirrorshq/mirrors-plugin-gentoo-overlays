#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import robust_layer
import mirrors.plugin


def main():
    dataDir = mirrors.plugin.params["storage-file"]["data-directory"]
    vcsType = mirrors.plugin.params["config"]["sync-type"]
    url = mirrors.plugin.params["config"]["sync-uri"]

    if vcsType == "git":
        robust_layer.simple_git.pull(dataDir, reclone_on_failure=True, url=url)
    elif vcsType == "svn":
        robust_layer.simple_subversion.update(dataDir, recheckout_on_failure=True, url=url)
    elif vcsType == "mercurial":
        # FIXME
        assert False
    elif vcsType == "rsync":
        # FIXME
        assert False
    else:
        assert False


###############################################################################

if __name__ == "__main__":
    main()
