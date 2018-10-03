"""Unit tests to exercise the interactive portions of the CRDS server."""

# from django.contrib.auth.models import User
from django.test import TransactionTestCase, TestCase

from crds import log
from crds_server import config as sconfig

class DatabaseBase(object):

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

    def get_dataset_ids(self, instr, datasets_since="1990-01-01T00:00:00"):   # swith space default date
        ids = db.get_dataset_ids(instr, datasets_since=datasets_since)

    def get_dataset_headers_by_id(self, instr, datasets_since="1990-01-01T00:00:00"):
        ids = db.get_dataset_ids(instrument=instr,  datasets_since=datasets_since)
        headers = db.get_dataset_headers_by_id(self.pmap, ids[:100])
        self.check_headers(headers)

if sconfig.observatory == "hst":
    
    from crds_server.xhst import database as db
    
    class Hst(DatabaseBase, TestCase):

        observatory = "hst"
        pmap = "hst_0355.pmap"
        
        @classmethod
        def setUpClass(cls, *args, **keys):
            log.info("DatabaseBase class setup start")
            log.set_verbose()
            db.init_db()
            log.info("DatabaseBase class setup end")

        # ACS -----------------------------------------------

        def test_get_dataset_headers_by_id_acs(self):
            self.get_dataset_headers_by_id("acs")

        def test_get_dataset_ids_acs(self):
            self.get_dataset_ids("acs")

        # COS -----------------------------------------------

        def test_get_dataset_headers_by_id_cos(self):
            self.get_dataset_headers_by_id("cos")

        def test_get_dataset_ids_cos(self):
            self.get_dataset_ids("cos")

        # NICMOS -----------------------------------------------

        def test_get_dataset_headers_by_id_nicmos(self):
            self.get_dataset_headers_by_id("nicmos")

        def test_get_dataset_ids_nicmos(self):
            self.get_dataset_ids("nicmos")

        # STIS -----------------------------------------------

        def test_get_dataset_headers_by_id_stis(self):
            self.get_dataset_headers_by_id("stis")

        def test_get_dataset_ids_stis(self):
            self.get_dataset_ids("stis")

        # WFC3 -----------------------------------------------

        def test_get_dataset_headers_by_id_wfc3(self):
            self.get_dataset_headers_by_id("wfc3")

        def test_get_dataset_ids_wfc3(self):
            self.get_dataset_ids("wfc3")

        # WFPC2 -----------------------------------------------

        def test_get_dataset_headers_by_id_wfpc2(self):
            self.get_dataset_headers_by_id("wfpc2")

        def test_get_dataset_ids_wfpc2(self):
            self.get_dataset_ids("wfpc2")

else:  # JWST
    
    from crds_server.xjwst import database as db

    class Jwst(DatabaseBase, TestCase):

        observatory = "jwst"
        pmap = "jwst_0063.pmap"

        @classmethod
        def setUpClass(cls, *args, **keys):
            log.info("DatabaseBase class setup start")
            log.set_verbose()
            log.info("DatabaseBase class setup end")

        # MIRI -----------------------------------------------


        def test_get_dataset_headers_by_id_miri(self):
            self.get_dataset_headers_by_id("miri")

        def test_get_dataset_ids_miri(self):
            self.get_dataset_ids("miri")

        # NIRCAM -----------------------------------------------

        def test_get_dataset_headers_by_id_nircam(self):
            self.get_dataset_headers_by_id("nircam")

        def test_get_dataset_ids_nircam(self):
            self.get_dataset_ids("nircam")

        # NIRISS -----------------------------------------------

        def test_get_dataset_headers_by_id_niriss(self):
            self.get_dataset_headers_by_id("niriss")

        def test_get_dataset_ids_niriss(self):
            self.get_dataset_ids("niriss")

        # NIRSPEC -----------------------------------------------

        def test_get_dataset_headers_by_id_nirspec(self):
            self.get_dataset_headers_by_id("nirspec")

        def test_get_dataset_ids_nirspec(self):
            self.get_dataset_ids("nirspec")

        # FGS -----------------------------------------------

        def test_get_dataset_headers_by_id_fgs(self):
            self.get_dataset_headers_by_id("fgs")

        def test_get_dataset_ids_fgs(self):
            self.get_dataset_ids("fgs")

