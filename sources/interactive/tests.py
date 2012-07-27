"""Unit tests to exercise the interactive portions of the CRDS server.
"""
import os

from django.test import TestCase

from crds import (rmap, utils, pysh)
import crds.config as lconfig

import crds.server.interactive.models as models
import crds.server.config as sconfig

from django.contrib.auth.models import User

HERE = os.path.dirname(__file__) or "."

class SimpleTest(TestCase):
    
    def runTest(self, *args, **keys):
        pass
    
    pmap = sconfig.observatory + ".pmap"
    
    def setUp(self): 
        User.objects.create_user('homer', 'homer@simpson.net', 'simpson')     
        self.fake_database_files([self.pmap])
        models.set_default_context(self.pmap)
        os.environ["CRDS_PATH"] = sconfig.install_root + "/test"
        utils.ensure_dir_exists(lconfig.get_crds_refpath())
        utils.ensure_dir_exists(lconfig.get_crds_mappath())
        
    def tearDown(self):
        if sconfig.observatory == "hst":
            delete_files = [
                "hst_0001.pmap",
                "hst_cos_0001.imap",
                "hst_acs_0001.imap",
                "hst_cos_deadtab_0001.rmap",
                "hst_acs_biasfile_0001.rmap",
                "hst_acs_dgeofile_0001.rmap",
                ]
        else:
            delete_files = [
                "jwst_0001.pmap",
                "jwst_miri_0001.imap",
                "jwst_nircam_0001.imap",
                "jwst_miri_flatfile_0001.rmap",
                "jwst_nircam_flatfile_0001.rmap",
                ]
        self.del_maps(delete_files)
        pysh.sh("/bin/rm -rf " + lconfig.get_crds_refpath(), raise_on_error=True)

    def authenticate(self):
        login = self.client.login(username="homer", password="simpson")
        self.assertTrue(login)
        
    def del_maps(self, maps):
        for map in maps:
            where = rmap.locate_mapping(map)
            try:
                os.remove(where)
            except OSError:
                pass
            try:
                os.remove(map)
            except OSError:
                pass

    def fake_database_files(self, files):
        for filename in files:
            name = os.path.basename(filename)
            location = filename if os.path.dirname(filename) else rmap.locate_file(filename, sconfig.observatory)
            models.add_crds_file(
                sconfig.observatory, name, location, 
                deliverer="homer", deliverer_email="homer@simpsons.com", 
                description="delivered by the man",
                add_slow_fields=False,
                state="delivered",
                update_derivation=False)
            models.AuditBlob.new("homer", "mass import", name, "becuz", "some details",
                                 observatory=sconfig.observatory)

    def assert_no_errors(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("ERROR:", response.content)
        
    def assert_has_error(self, response, msg=None):
        self.assertEqual(response.status_code, 200)
        self.assertIn("ERROR:", response.content)
        if msg is not None:
            self.assertIn(msg, response.content)

    def test_index(self):
        response = self.client.get('/')
        self.assert_no_errors(response)

#    def test_login(self):
#        response = self.client.post("/login/", 
#                {"username":"you", "password":"lemme guess"})
#self.assert_no_errors(response)
    
    def test_logout(self):
        response = self.client.get("/logout/") 
        self.assert_no_errors(response)
    
    def test_bestrefs(self):
        response = self.client.get("/bestrefs/")
        self.assert_no_errors(response)
    
    # XXX Implement bestrefs tests
    def test_bestrefs_post_archive_dataset(self):
        pass
    
    def test_bestrefs_post_default_context(self):
        pass
    
    def test_bestrefs_post_uploaded_dataset(self):
        if sconfig.observatory == "hst":
            dataset1 = "interactive/test_data/j8bt05njq_raw.fits"
        else:
            dataset1 = "interactive/test_data/jwst_fake_raw.fits"
        response = self.client.post("/bestrefs/", {
            "pmap_mode" : "pmap_text",
            "pmap_text" : self.pmap,
            "dataset_mode" : "dataset_uploaded",
            "dataset_uploaded" : open(dataset1),
            })  
        self.assert_no_errors(response)
    
    def test_submit_get(self):
        self.authenticate()
        response = self.client.get("/submit/reference/")
        self.assert_no_errors(response)

    def test_submit_post(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            rmap1 = "interactive/test_data/hst_cos_deadtab.rmap"
            self.fake_database_files([
                "interactive/test_data/s7g1700gl_dead.fits", 
                "interactive/test_data/s7g1700ql_dead.fits",]) 
        else:
            rmap1 = "interactive/test_data/jwst_miri_flatfile.rmap"
            self.fake_database_files([
                "interactive/test_data/jwst_miri_flatfile_0001.fits",])
        rmap2 = self.add_1(rmap1)
        response = self.client.post("/submit/mapping/", {
            "observatory" : sconfig.observatory,
            "auto_rename" : "on",
            "submitted_file" : open(rmap1),
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "creator" : "Somebody else",
            })
        self.assert_no_errors(response)
        self.assertIn(rmap2, response.content)
    
    def test_blacklist_get(self):
        self.authenticate()
        response = self.client.get("/blacklist/")
        self.assert_no_errors(response)

    def test_blacklist_post(self):
        if sconfig.observatory == "hst":
            imap = "hst_acs.imap"
            rmap = "hst_acs_biasfile.rmap"            
        else:
            imap = "jwst_miri.imap"
            rmap = "jwst_miri_flatfile.rmap"
        self.authenticate()
        self.fake_database_files([imap, rmap])
        response = self.client.post("/blacklist/", {
            "observatory" : sconfig.observatory,
            "file_known" : rmap,
            "badflag" : "bad",
            "why" : "just had a feeling.",
            })
        # print response.content
        self.assert_no_errors(response)
        self.assertTrue(self.pmap in response.content)
        self.assertTrue(imap in response.content)
        self.assertTrue(rmap in response.content)

    def test_certify_get(self):
        self.authenticate()
        response = self.client.get("/certify/")
        self.assert_no_errors(response)

    def test_certify_post_fits_uploaded(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            fits = "interactive/test_data/s7g1700gl_dead.fits"
        else:
            fits = "interactive/test_data/jwst_miri_flatfile.fits"
        self.fake_database_files([fits])
        response = self.client.post("/certify/", {
            "filemode" : "file_uploaded",
            "file_uploaded" : open(fits),
        })
        self.assert_no_errors(response)
        self.assertIn("0 errors", response.content)
        self.assertEqual(response.content.count("OK"), 3)

    def test_certify_post_rmap_known(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            rmap = "hst_cos_deadtab.rmap"
        else:
            rmap = "jwst_miri_flatfile.rmap"
        self.fake_database_files([rmap])
        response = self.client.post("/certify/", {
            "filemode" : "file_known",
            "file_known" : rmap,
        })
        self.assert_no_errors(response)
        self.assertTrue(response.content.count("0 errors") == 1)
        self.assertNotIn("Failed", response.content)
        self.assertEqual(response.content.count("OK"), 2)

#    def test_certify_post_rmap_uploaded(self):
#        self.authenticate()
#        response = self.client.post("/certify/", {
#            "filemode" : "file_uploaded",
#            "file_uploaded" : "interactive/hst_cos_deadmap.rmap",
#        })
#        print response.content
#        self.assert_no_errors(response)
#        self.assertTrue(response.content.count("0 errors") == 1)
#        self.assertTrue("Failed" not in response.content)
#        self.assertTrue(response.content.count("OK") == 2)

    def test_difference_get(self):
        response = self.client.get("/difference/")
        self.assert_no_errors(response)

    def test_difference_post(self):
        if sconfig.observatory == "hst":
            file1 = "hst_acs.imap"
            file2 = "hst_cos.imap"
        else:
            file1 = "jwst_miri.imap"
            file2 = "jwst_nircam.imap"
        self.fake_database_files([file1, file2])
        response = self.client.post("/difference/", {
            "filemode1": "file_known1",
            "file_known1" : file1,
            "filemode2": "file_known2",
            "file_known2" : file2,
        })
        self.assert_no_errors(response)
    
    def test_recent_activity_get(self):
        self.authenticate()
        response = self.client.get("/recent_activity/")
        self.assert_no_errors(response)

    def test_recent_activity_post(self):
        self.authenticate()
        response = self.client.post("/recent_activity/", {
                "action" : "new context",
                "observatory" : "*",
                "instrument" : "*",
                "filekind" : "*",
                "extension" : "*",
                "filename" : "*",
                "deliverer_user" : "*",
            })
        self.assert_no_errors(response)

    def test_create_contexts(self):
        self.authenticate()
        response = self.client.get("/create_contexts/")
        self.assert_no_errors(response)
        
    def add_1(self, name):
        """hst.pmap -->  hst_0001.pmap"""
        ext = "." + os.path.splitext(name)[-1]
        return os.path.basename(name).replace(ext, "_0001" + ext)

    def test_create_contexts_post(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            rmap1 = "hst_acs_biasfile.rmap"
            rmap2 = "hst_cos_deadtab.rmap"
        else:
            rmap1 = "jwst_miri_flatfile.rmap"
            rmap2 = "jwst_nircam_flatfile.rmap"
        self.fake_database_files([rmap1, rmap2])
        response = self.client.post("/create_contexts/", {
                "pmap_mode" : "pmap_text",
                "pmap_text" : self.pmap,
                "rmaps" : rmap1 + ", " + rmap2,
                "description" : "updated rmaps"
            })
        self.assert_no_errors(response)
        self.assertTrue(self.add_1(self.pmap) in response.content)
        self.assertTrue(self.add_1(rmap1) in response.content)
        self.assertTrue(self.add_1(rmap2) in response.content)
    
    def test_browse_file(self):
        response = self.client.get("/browse/" + self.pmap)
        self.assert_no_errors(response)

    def test_browse_db_get(self):
        self.authenticate()
        response = self.client.get("/browse_db/")
        self.assert_no_errors(response)

    def test_browse_db_post(self):
        self.authenticate()
        response = self.client.post("/browse_db/", {
                "observatory" : sconfig.observatory,
                "instrument" : "*",
                "filekind" : "*",
                "extension": "*",
                "filename": self.pmap,
                "deliverer_user": "*",
                "status":"*",
            })
        # print response
        self.assert_no_errors(response)
        self.assertTrue(self.pmap in response.content)
        self.assertEqual(response.content.count("<tr>"), 4)

    def test_edit_rmap_replace(self):
        pass

    def test_edit_rmap_insert(self):
        pass
    
    def test_batch_submit_replace(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            reference = "interactive/test_data/s7g1700gl_dead.fits"
        else:
            reference = "interactive/test_data/jwst_miri_flatfile.fits"
        response = self.client.post("/batch_submit_reference/", {
                "pmap_mode" : "pmap_default",
                "pmap_default" : self.pmap,
                "file_uploaded" : open(reference),
                "description":"this is only a test.",
            })
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Abort", response.content)
        self.assertIn("REPLACE", response.content)
        self.assertNotIn("INSERT", response.content)

    def test_batch_submit_insert(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            reference = "interactive/test_data/s7g1700gm_dead.fits"
        else:
            reference = "interactive/test_data/jwst_miri_flatfile_insert.fits"
        response = self.client.post("/batch_submit_reference/", {
                "pmap_mode" : "pmap_default",
                "pmap_default" : self.pmap,
                "file_uploaded" : open(reference),
                "description":"this is only a test.",
            })
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Abort", response.content)
        self.assertIn("INSERT", response.content)
        self.assertNotIn("REPLACE", response.content)

