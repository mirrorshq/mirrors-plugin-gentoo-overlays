#!/usr/bin/python3
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

import time
import json
import signal
import robust_layer
import lxml.etree
import urllib.request
import mirrors.mirror_site_factory
from datetime import datetime


REFRESH_INTERVAL = 3600     # refresh every 1 hour
RETRY_INTERVAL = 60         # retry after 1 minute


def official_overlays():
    url = "https://api.gentoo.org/overlays/repositories.xml"
    cList = [
        ("git", "https"),
        ("git", "http"),
        ("git", "git"),
        ("svn", "https"),
        ("svn", "http"),
        ("mercurial", "https"),
        ("mercurial", "http"),
        ("rsync", "rsync"),
    ]

    with mirrors.mirror_site_factory.ApiClient() as sock:
        # config
        bAllOverlay = None          # enable all overlays
        whileList = None            # overlay name white list
        blackList = None            # overlay name black list
        if True:
            cfgDict = mirrors.mirror_site_factory.params["config"]
            if "white-list" in cfgDict:
                whileList = cfgDict["white-list"]
                if "*" in whileList:
                    bAllOverlay = True
            else:
                bAllOverlay = False
                whileList = None
            if "black-list" in cfgDict:
                blackList = cfgDict["black-list"]
            else:
                blackList = []

        lastModifiedTm = None
        overlayDict = dict()
        while True:
            print("Refreshing...")

            # get latest overlay database
            rootElem = None
            try:
                resp = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=robust_layer.TIMEOUT)
                remoteTm = datetime.strptime(resp.info().get("Last-Modified"), "%a, %d %b %Y %H:%M:%S %Z")
                if lastModifiedTm is not None and remoteTm <= lastModifiedTm:
                    time.sleep(REFRESH_INTERVAL)
                    continue

                resp = urllib.request.urlopen(url, timeout=robust_layer.TIMEOUT)
                rootElem = lxml.etree.parse(resp).getroot()
                lastModifiedTm = remoteTm
            except Exception:
                print("    Failed, retry in 1 minute...")
                time.sleep(RETRY_INTERVAL)
                continue

            # parse overlay database
            newOverlayDict = dict()
            for nameTag in rootElem.xpath(".//repo/name"):
                overlayName = nameTag.text
                msId = _overName2MsId(overlayName)

                # fiter overlays by configuration
                if overlayName in blackList:
                    continue
                if not bAllOverlay and whileList is not None and overlayName not in whileList:
                    continue

                # check
                if msId in newOverlayDict:
                    print("    Duplicate overlay \"%s\"" % (overlayName))
                    continue

                # get overlay information
                for vcsType, urlPrefix in cList:
                    for sourceTag in nameTag.xpath("../source"):
                        tVcsType = sourceTag.get("type")
                        tUrl = sourceTag.text
                        if tVcsType == vcsType and tUrl.startswith(urlPrefix + "://"):
                            newOverlayDict[msId] = (tVcsType, tUrl)
                            break
                    if msId in newOverlayDict:
                        break
                if msId not in newOverlayDict:
                    print("    No appropriate source for overlay \"%s\"" % (overlayName))
                    continue

                # FIXME: we only supports git and svn
                if newOverlayDict[msId][0] not in ["git", "svn"]:
                    del newOverlayDict[msId]

            # send remove messages
            for msId in overlayDict:
                if msId not in newOverlayDict:
                    sock.remove_mirror_site(_msId2DistfilesMsId(msId))
                    sock.remove_mirror_site(msId)
                else:
                    if overlayDict[msId] != newOverlayDict[msId]:
                        sock.remove_mirror_site(_msId2DistfilesMsId(msId))
                        sock.remove_mirror_site(msId)
                        del overlayDict[msId]

            # send add messages
            for msId in newOverlayDict:
                if msId not in overlayDict:
                    vcsType = newOverlayDict[msId][0]
                    url = newOverlayDict[msId][1]
                    sock.add_mirror_site(_genMetadataXml(msId), _genCfgJson(vcsType, url))
                    sock.add_mirror_site(_genDistfilesMetadataXml(msId), _genCfgJson(vcsType, url))

            # next cycle
            overlayDict = newOverlayDict
            time.sleep(REFRESH_INTERVAL)


def wild_overlays():
    with mirrors.mirror_site_factory.ApiClient() as sock:
        cfgDict = mirrors.mirror_site_factory.params["config"]

        # send add messages
        for item in cfgDict:
            msId = _overName2MsId(item["overlay-name"])
            vcsType = item["sync-type"]
            url = item["sync-uri"]
            sock.add_mirror_site(_genMetadataXml(msId), _genCfgJson(vcsType, url))
            sock.add_mirror_site(_genDistfilesMetadataXml(msId), _genCfgJson(vcsType, url))

        # sleep forever
        while True:
            signal.pause()


def _overName2MsId(overlayName):
    return "gentoo-overlay-" + overlayName


def _msId2DistfilesMsId(msId):
    return msId + "-distfiles"


def _genMetadataXml(msId):
    buf = ''
    buf += '<mirror-site id="%s">\n' % (msId)
    buf += '  <name>%s</name>\n' % (msId)
    buf += '  <storage type="file"/>\n'
    buf += '  <advertiser type="rsync"/>\n'
    buf += '  <initializer>\n'
    buf += '    <executable>updater.py</executable>\n'
    buf += '  </initializer>\n'
    buf += '  <updater>\n'
    buf += '    <executable>updater.py</executable>\n'
    buf += '    <schedule type="interval">4h</schedule>\n'
    buf += '  </updater>\n'
    buf += '</mirror-site>\n'
    return buf


def _genDistfilesMetadataXml(msId):
    buf = ''
    buf += '<mirror-site id="%s">\n' % (_msId2DistfilesMsId(msId))
    buf += '  <name>%s</name>\n' % (_msId2DistfilesMsId(msId))
    buf += '  <storage type="file"/>\n'
    buf += '  <advertiser type="httpdir"/>\n'
    buf += '  <need-temp-directory/>\n'
    buf += '  <initializer>\n'
    buf += '    <executable>updater_distfiles.py</executable>\n'
    buf += '  </initializer>\n'
    buf += '  <updater>\n'
    buf += '    <executable>updater_distfiles.py</executable>\n'
    buf += '    <schedule type="interval">4h</schedule>\n'
    buf += '  </updater>\n'
    buf += '</mirror-site>\n'
    return buf


def _genCfgJson(vcsType, url):
    data = dict()
    data["sync-type"] = vcsType
    data["sync-uri"] = url
    return json.dumps(data)


###############################################################################

if __name__ == "__main__":
    if mirrors.mirror_site_factory.params["id"] == "gentoo-overlays":
        official_overlays()
    elif mirrors.mirror_site_factory.params["id"] == "gentoo-wild-overlays":
        wild_overlays()
    else:
        assert False
