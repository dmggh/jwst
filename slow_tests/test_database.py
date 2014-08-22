"""Unit tests to exercise the interactive portions of the CRDS server."""

# import sys
# import os
# import shutil
# import os.path

# from django.contrib.auth.models import User
from django.test import TransactionTestCase, TestCase

from crds import log
from crds.server import config as sconfig
from crds.server.interactive import database as db

class DatabaseBase(object):

    @classmethod
    def setUpClass(cls, *args, **keys):
        log.info("DatabaseBase class setup start")
        log.set_verbose()
        db.init_db()
        log.info("DatabaseBase class setup end")

    @classmethod
    def tearDownClass(self):
        pass
        
    def runTest(self, *args, **keys):
        pass
    
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def check_headers(self, headers):
        for source in headers:
            assert not isinstance(headers[source], str), \
                "Header fetch failed for " + repr(source) + " : " + repr(headers[source])

    def get_dataset_headers_by_instrument(self, instr):
        headers = db.get_dataset_headers_by_instrument(instr, self.observatory)
        self.check_headers(headers)

        # log.info("get_headers_by_instrument('{}')".format(instr), "->", len(headers))

    def get_dataset_ids(self, instr):
        ids = db.get_dataset_ids(instr, self.observatory)

    def get_dataset_headers_by_id(self, instr):
        ids = db.get_dataset_ids(instr, self.observatory)
        headers = db.get_dataset_headers_by_id(ids[:100], self.observatory)
        self.check_headers(headers)

if sconfig.observatory == "hst":
    
    class Hst(DatabaseBase, TestCase):

        def __init__(self, *args, **keys):
            super(Hst, self).__init__(*args, **keys)
        
        observatory = "hst"
        
        # ACS -----------------------------------------------

        def test_get_dataset_headers_by_instrument_acs(self):
            self.get_dataset_headers_by_instrument("acs")

        def test_get_dataset_headers_by_id_acs(self):
            self.get_dataset_headers_by_id("acs")

        def test_get_dataset_ids_acs(self):
            self.get_dataset_ids("acs")

        # COS -----------------------------------------------

        def test_get_dataset_headers_by_instrument_cos(self):
            self.get_dataset_headers_by_instrument("cos")

        def test_get_dataset_headers_by_id_cos(self):
            self.get_dataset_headers_by_id("cos")

        def test_get_dataset_ids_cos(self):
            self.get_dataset_ids("cos")

        # NICMOS -----------------------------------------------

        def test_get_dataset_headers_by_instrument_nicmos(self):
            self.get_dataset_headers_by_instrument("nicmos")

        def test_get_dataset_headers_by_id_nicmos(self):
            self.get_dataset_headers_by_id("nicmos")

        def test_get_dataset_ids_nicmos(self):
            self.get_dataset_ids("nicmos")

        # STIS -----------------------------------------------

        def test_get_dataset_headers_by_instrument_stis(self):
            self.get_dataset_headers_by_instrument("stis")

        def test_get_dataset_headers_by_id_stis(self):
            self.get_dataset_headers_by_id("stis")

        def test_get_dataset_ids_stis(self):
            self.get_dataset_ids("stis")

        # WFC3 -----------------------------------------------

        def test_get_dataset_headers_by_instrument_wfc3(self):
            self.get_dataset_headers_by_instrument("wfc3")

        def test_get_dataset_headers_by_id_wfc3(self):
            self.get_dataset_headers_by_id("wfc3")

        def test_get_dataset_ids_wfc3(self):
            self.get_dataset_ids("wfc3")

        # WFPC2 -----------------------------------------------

        def test_get_dataset_headers_by_instrument_wfpc2(self):
            self.get_dataset_headers_by_instrument("wfpc2")

        def test_get_dataset_headers_by_id_wfpc2(self):
            self.get_dataset_headers_by_id("wfpc2")

        def test_get_dataset_ids_wfpc2(self):
            self.get_dataset_ids("wfpc2")

else:  # JWST
    
    class Jwst(InteractiveBase, TransactionTestCase):

        def __init__(self, *args, **keys):
            super(Jwst, self).__init__(*args, **keys)

        observatory = "jwst"
