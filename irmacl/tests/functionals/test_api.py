# Copyright (c) 2013-2018 Quarkslab.
# This file is part of IRMA project.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the top-level directory
# of this distribution and at:
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# No part of the project, including this file, may be copied,
# modified, propagated, or distributed except according to the
# terms contained in the LICENSE file.

import unittest
import os
import re
import time
import tempfile
import hashlib
from irmacl.apiclient import IrmaFileExt, IrmaError
from irmacl.helpers import probe_list, data_upload, file_download, about, \
    file_upload, scan_data, scan_files, scan_get, scan_launch, \
    scan_proberesults, file_search, scan_cancel, tag_list, file_tag_add, \
    file_tag_remove

import requests


cwd = os.path.dirname(__file__)
SAMPLES_DIR = os.path.join(cwd, "samples")
FILENAMES = ["fish", "ls"]
HASHES = ["7cddf3fa0f8563d49d0e272208290fe8fdc627e5cae0083d4b7ecf901b2ab6c8",
          "71f30d658966bcc7ea162b4e0f20d2305d4a003e854305b524280f4c2a3b48a3",
          "3826e18a5dc849670744752fd27c4eec6136ac90",
          "8d50d7a3929a356542119aa858c492442655e097",
          "07edba6f3f181bad9a56a87d4039487a",
          "e718241e1cc6472d4f4bac20c59a0179"]
FILEPATHS = list(map(lambda x: os.path.join(SAMPLES_DIR, x), FILENAMES))

SESSION = requests.Session()


class IrmaAPITests(unittest.TestCase):

    def _validate_uuid(self, uuid):
        regex = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',
                           re.IGNORECASE)
        return regex.match(uuid) is not None

    def _check_scan(self, scan, scanid, range_status, filelist,
                    range_finished, range_total,
                    force, mimetype_filtering, resubmit_files):
        nb_files = len(filelist)
        self.assertEqual(scan.id, scanid)
        self.assertIn(scan.pstatus, range_status)
        self.assertEqual(type(scan.results), list)
        self.assertEqual(len(scan.results), nb_files)
        self.assertIn(scan.probes_finished, range_finished)
        self.assertIn(scan.probes_total, range_total)
        self.assertEqual(scan.force, force)
        self.assertEqual(scan.mimetype_filtering, mimetype_filtering)
        self.assertEqual(scan.resubmit_files, resubmit_files)


class IrmaAPIScanTests(IrmaAPITests):

    def test_probe_list(self):
        probelist = probe_list(session=SESSION)
        self.assertIs(type(probelist), list)
        self.assertNotEqual(len(probelist), 0)

    def test_file_upload(self):
        fw = file_upload(FILEPATHS[0], session=SESSION)
        self.assertEqual(fw.name, FILENAMES[0])
        self.assertEqual(fw.scan_id, None)

    def test_data_upload(self):
        with open(FILEPATHS[0], "rb") as f:
            data = f.read()
        fw = data_upload(data, FILENAMES[0], session=SESSION)
        self.assertEqual(fw.name, FILENAMES[0])
        self.assertEqual(fw.scan_id, None)

    def test_scan_launch(self):
        force = False
        probes = probe_list(session=SESSION)
        nb_jobs = len(FILENAMES) * len(probes)
        scan = scan_files(FILEPATHS, force, probe=probes, blocking=True,
                          session=SESSION)
        self._check_scan(scan, scan.id, ["finished"],
                         FILENAMES, range(nb_jobs+1), range(nb_jobs+1),
                         force, True, True)

    def test_scan_force(self):
        filelist = [FILENAMES[0]]
        force = False
        probes = [probe_list(session=SESSION)[0]]
        nb_jobs = len(filelist) * len(probes)
        scan = scan_files([FILEPATHS[0]], force, probe=probes, session=SESSION)
        self._check_scan(scan, scan.id, ["ready", "uploaded",
                                         "launched", "finished"],
                         filelist, range(nb_jobs + 1), range(nb_jobs + 1),
                         force, True, True)
        try:
            scan_cancel(scan.id, session=SESSION)
        except IrmaError:
            # could happen if scan is already finished
            pass

    def test_mimetype_filtering(self):
        force = True
        mimetype_filtering = False
        probes = probe_list(session=SESSION)
        nb_jobs = len(FILENAMES) * len(probes)
        scan = scan_files(FILEPATHS, force, probes,
                          mimetype_filtering=mimetype_filtering,
                          session=SESSION)
        self._check_scan(scan, scan.id, ["ready", "uploaded",
                                         "launched", "finished"],
                         FILENAMES, range(nb_jobs + 1), range(nb_jobs + 1),
                         force, mimetype_filtering, True)

        try:
            scan = scan_cancel(scan.id, session=SESSION)
            self._check_scan(scan, scan.id, ["cancelled"],
                             FILENAMES, range(nb_jobs + 1), range(nb_jobs + 1),
                             force, mimetype_filtering, True)
        except IrmaError:
            self._check_scan(scan, scan.id, ["finished"],
                             FILENAMES, [nb_jobs], [nb_jobs],
                             force, mimetype_filtering, True)

    def test_resubmit_files(self):
        force = True
        resubmit_files = False
        probes = probe_list(session=SESSION)
        nb_jobs = len(FILENAMES) * len(probes)
        scan = scan_files(FILEPATHS, force, probe=probes,
                          resubmit_files=resubmit_files, session=SESSION)
        self._check_scan(scan, scan.id, ["ready", "uploaded",
                                         "launched", "finished"],
                         FILENAMES, range(nb_jobs + 1), range(nb_jobs + 1),
                         force, True, resubmit_files)
        try:
            scan = scan_cancel(scan.id, session=SESSION)
            self._check_scan(scan, scan.id, ["cancelled"],
                             FILENAMES, range(nb_jobs + 1), range(nb_jobs + 1),
                             force, True, resubmit_files)
        except IrmaError:
            self._check_scan(scan, scan.id, ["finished"],
                             FILENAMES, [nb_jobs], [nb_jobs],
                             force, True, resubmit_files)

    def test_scan_files(self):
        force = True
        probes = probe_list(session=SESSION)
        nb_jobs = len(FILENAMES) * len(probes)
        scan = scan_files(FILEPATHS, force, probe=probes, session=SESSION)
        self._check_scan(scan, scan.id, ["ready", "uploaded",
                                         "launched", "finished"],
                         FILENAMES, range(nb_jobs + 1), range(nb_jobs + 1),
                         True, True, True)
        try:
            scan = scan_cancel(scan.id, session=SESSION)
            self._check_scan(scan, scan.id, ["cancelled"],
                             FILENAMES, range(nb_jobs + 1), range(nb_jobs + 1),
                             force, True, True)
        except IrmaError:
            self._check_scan(scan, scan.id, ["finished"],
                             FILENAMES, [nb_jobs], [nb_jobs],
                             force, True, True)

    def test_scan_data(self):
        force = True
        probes = probe_list(session=SESSION)
        nb_jobs = len(probes)
        with open(FILEPATHS[0], "rb") as f:
            data = f.read()
        scan = scan_data(data, FILENAMES[0], force, probe=probes,
                         session=SESSION)
        self._check_scan(scan, scan.id, ["ready", "uploaded",
                                         "launched", "finished"],
                         [FILENAMES[0]], range(nb_jobs + 1),
                         range(nb_jobs + 1), True, True, True)
        try:
            scan = scan_cancel(scan.id, session=SESSION)
            self._check_scan(scan, scan.id, ["cancelled"],
                             [FILENAMES[0]], range(nb_jobs + 1),
                             range(nb_jobs + 1), force, True, True)
        except IrmaError:
            self._check_scan(scan, scan.id, ["finished"],
                             [FILENAMES[0]], [nb_jobs], [nb_jobs],
                             force, True, True)

    def test_scan_files_timeout(self):
        force = True
        probes = probe_list(session=SESSION)
        with self.assertRaises(IrmaError):
            scan_files(FILEPATHS, force, probe=[probes[0]], blocking=True,
                       blocking_timeout=0, session=SESSION)

    def test_scan_get(self):
        force = False
        probes = probe_list(session=SESSION)
        scan = scan_files(FILEPATHS, force, probe=probes, blocking=True,
                          session=SESSION)
        self._check_scan(scan, scan.id, ["finished"],
                         FILENAMES, [scan.probes_total], [scan.probes_total],
                         force, True, True)

    def test_file_results_formatted(self):
        force = True
        probes = probe_list(session=SESSION)
        scan = scan_files(FILEPATHS, force, mimetype_filtering=False,
                          probe=probes, blocking=True, session=SESSION)
        for result in scan.results:
            self.assertTrue(self._validate_uuid(str(result.id)))
            res = scan_proberesults(result.id, session=SESSION)
            self.assertIn(res.name, FILENAMES)
            self.assertEqual(type(res.probe_results), dict)
            results_cnt = sum(len(rs) for rs in res.probe_results.values())
            self.assertEqual(results_cnt, res.probes_finished)

    def test_file_results_not_formatted(self):
        force = True
        probes = probe_list(session=SESSION)
        scan = scan_files(FILEPATHS, force, mimetype_filtering=False,
                          probe=probes, blocking=True, session=SESSION)
        for result in scan.results:
            self.assertTrue(self._validate_uuid(str(result.id)))
            res = scan_proberesults(result.id, formatted=False,
                                    session=SESSION)
            self.assertIn(res.name, FILENAMES)
            self.assertEqual(type(res.probe_results), dict)
            results_cnt = sum(len(rs) for rs in res.probe_results.values())
            self.assertEqual(results_cnt, res.probes_finished)

    def test_scan_empty_data(self):
        force = True
        probes = probe_list(session=SESSION)
        nb_jobs = len(probes)
        filename = "empty_file"
        scan = scan_data("", filename, force, probe=probes, session=SESSION)
        self._check_scan(scan, scan.id, ["ready", "uploaded",
                                         "launched", "finished"],
                         [filename], range(nb_jobs + 1),
                         range(nb_jobs + 1), True, True, True)
        try:
            scan = scan_cancel(scan.id, session=SESSION)
            self._check_scan(scan, scan.id, ["cancelled"],
                             [filename], range(nb_jobs + 1),
                             range(nb_jobs + 1), force, True, True)
        except IrmaError:
            self._check_scan(scan, scan.id, ["finished"],
                             [filename], [nb_jobs], [nb_jobs],
                             force, True, True)

    def test_scan_empty_file(self):
        force = True
        probes = probe_list(session=SESSION)
        nb_jobs = len(probes)
        filename = "empty_file"
        filepath = os.path.join(SAMPLES_DIR, filename)

        scan = scan_files([filepath], force, probe=probes, session=SESSION)
        self._check_scan(scan, scan.id, ["ready", "uploaded",
                                         "launched", "finished"],
                         [filename], range(nb_jobs + 1),
                         range(nb_jobs + 1), True, True, True)
        try:
            scan = scan_cancel(scan.id, session=SESSION)
            self._check_scan(scan, scan.id, ["cancelled"],
                             [filename], range(nb_jobs + 1),
                             range(nb_jobs + 1), force, True, True)
        except IrmaError:
            self._check_scan(scan, scan.id, ["finished"],
                             [filename], [nb_jobs], [nb_jobs],
                             force, True, True)


class IrmaAPIFileTests(IrmaAPITests):

    def test_file_search_name(self):
        force = False
        probes = probe_list(session=SESSION)
        scan_files(FILEPATHS, force, probe=probes, blocking=True,
                   session=SESSION)
        for name in FILENAMES:
            data = file_search(name=name, session=SESSION)
            self.assertEqual(type(data), tuple)
            (total, res) = file_search(name, limit=1, session=SESSION)
            self.assertEqual(type(res), list)
            self.assertEqual(type(res[0]), IrmaFileExt)
            self.assertEqual(len(res), 1)
            self.assertEqual(type(total), int)

    def test_file_search_limit(self):
        (total, _) = file_search(session=SESSION)
        if total > 10:
            offset = total - 10
            limit = 10
        else:
            offset = 0
            limit = total
        (_, res) = file_search(offset=offset, limit=limit, session=SESSION)
        self.assertEqual(type(res), list)
        self.assertEqual(len(res), limit)

    def test_file_search_hash(self):
        force = False
        probes = probe_list(session=SESSION)
        scan_files(FILEPATHS, force, probe=probes, blocking=True,
                   session=SESSION)
        for hash in HASHES:
            (_, res) = file_search(hash=hash, session=SESSION)
            self.assertTrue(len(res) > 0)
            self.assertEqual(type(res[0]), IrmaFileExt)

    def test_file_search_hash_name(self):
        with self.assertRaises(IrmaError):
            file_search(name="name", hash="hash", session=SESSION)

    def test_file_download(self):
        scan_files([FILEPATHS[0]], False, blocking=True, session=SESSION)
        dst = tempfile.NamedTemporaryFile(delete=False)
        file_download(HASHES[0], dst.name, session=SESSION)
        hash = hashlib.sha256()
        with open(dst.name, "rb") as f:
            hash.update(f.read())
        os.unlink(dst.name)
        hashval = hash.hexdigest()
        self.assertEqual(hashval, HASHES[0])


class IrmaAPIAboutTests(IrmaAPITests):

    def test_about(self):
        res = about(session=SESSION)
        self.assertTrue("version" in res)


class IrmaAPITagTests(IrmaAPITests):
    taglist = None
    file_sha256 = HASHES[0]
    file_path = FILEPATHS[0]
    file_name = FILENAMES[0]
    result = None
    former_tag = []

    def setUp(self):
        if self.taglist is None:
            self.taglist = tag_list()
        if len(self.taglist) == 0:
            raise unittest.SkipTest("Skipping No tag found (please add some)")
        # Insure file is present (Force=False)
        scan = scan_files([self.file_path], False, blocking=True,
                          session=SESSION)
        self.result = scan_proberesults(scan.results[0].id, session=SESSION)
        # Insure file got no tags for test
        self.former_tag = [x.id for x in self.result.file_infos.tags]
        if len(self.former_tag) != 0:
            for tagid in self.former_tag:
                file_tag_remove(self.file_sha256, tagid)
            self.result = scan_proberesults(scan.results[0].id,
                                            session=SESSION)

    def tearDown(self):
        self.assertEqual(self.file_sha256, self.result.file_sha256)
        self.assertEqual(self.file_sha256, self.result.file_infos.sha256)
        self.result = scan_proberesults(self.result.id, session=SESSION)
        for tag in self.result.file_infos.tags:
            file_tag_remove(self.file_sha256, tag.id)
        for tagid in self.former_tag:
            file_tag_add(self.file_sha256, tagid)

    def test_tag_list(self):
        for tag in tag_list():
            self.assertIn(tag.id, [x.id for x in self.taglist])
            self.assertIn(tag.text, [x.text for x in self.taglist])

    def test_file_tag_add_remove(self):
        for tag in self.taglist:
            file_tag_add(self.file_sha256, tag.id, session=SESSION)
            result = scan_proberesults(self.result.id, session=SESSION)
            self.assertIn(tag.id,
                          [x.id for x in result.file_infos.tags])
        for tag in self.taglist:
            file_tag_remove(self.file_sha256, tag.id, session=SESSION)
            result = scan_proberesults(self.result.id, session=SESSION)
            self.assertNotIn(tag.id,
                             [x.id for x in result.file_infos.tags])

    def test_file_search_tag(self):
        self.assertEqual(len(self.result.file_infos.tags), 0)
        tagged = []
        for tag in self.taglist:
            file_tag_add(self.file_sha256, tag.id, session=SESSION)
            tagged.append(tag.id)
            (total, found) = file_search(name=self.file_name, tags=tagged,
                                         session=SESSION)
            self.assertGreater(total, 0)
            self.assertIn(self.file_name, [x.name for x in found])

    def test_file_search_not_existing_tag(self):
        invalid_tagid = max([x.id for x in self.taglist]) + 1
        with self.assertRaises(IrmaError):
            file_search(tags=[invalid_tagid], session=SESSION)

    def test_file_search_not_existing_tag_and_name(self):
        invalid_tagid = max([x.id for x in self.taglist]) + 1
        with self.assertRaises(IrmaError):
            file_search(name=self.file_name, tags=[invalid_tagid],
                        session=SESSION)

    def test_file_tag_twice(self):
        found = file_search(hash=self.file_sha256, session=SESSION)
        self.assertNotEqual(len(found), 0)
        file_tag_add(self.file_sha256, self.taglist[0].id, session=SESSION)
        (total, found) = file_search(hash=self.file_sha256, session=SESSION)
        self.assertGreaterEqual(total, 1)
        with self.assertRaises(IrmaError):
            file_tag_add(self.file_sha256, self.taglist[0].id)


if __name__ == "__main__":
    unittest.main()
