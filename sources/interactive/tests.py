"""Unit tests to exercise the interactive portions of the CRDS server.
"""
import os

from django.test import TestCase

import crds.rmap as rmap
import crds.server.interactive.models as models

from django.contrib.auth.models import User

class SimpleTest(TestCase):
    
    def runTest(self, *args, **keys):
        pass
    
    def setUp(self): 
        User.objects.create_user('homer', 'homer@simpson.net', 'simpson')     
        self.fake_database_files(["hst.pmap"])
        models.set_default_context("hst.pmap")

    def tearDown(self):
        self.del_maps(["hst_0001.pmap",
                       "hst_cos_0001.imap",
                       "hst_acs_0001.imap",
                       "hst_cos_deadtab_0001.rmap",
                       "hst_acs_biasfile_0001.rmap",
                       "hst_acs_dgeofile_0001.rmap",
                       ])

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

    def fake_database_files(self, files, observatory="hst"):
        for filename in files:
            name = os.path.basename(filename)
            location = filename if os.path.dirname(filename) else rmap.locate_file(filename, observatory)
            models.add_crds_file(
                observatory, name, location, 
                deliverer="homer", deliverer_email="homer@simpsons.com", 
                description="delivered by the man",
                add_slow_fields=False,
                state="delivered",
                update_derivation=False)
            models.AuditBlob.new("homer", "mass import", name, "becuz", "some details",
                                 observatory=observatory)

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
        response = self.client.post("/bestrefs/", {
            "pmap_mode" : "pmap_text",
            "pmap_text" : "hst.pmap",
            "dataset_mode" : "dataset_uploaded",
            "dataset_uploaded" : open("interactive/test_data/j8bt05njq_raw.fits"),
            })  
        self.assert_no_errors(response)
    
    def test_submit_get(self):
        self.authenticate()
        response = self.client.get("/submit/reference/")
        self.assert_no_errors(response)

    def test_submit_post(self):
        self.authenticate()
        self.fake_database_files([
                "interactive/test_data/s7g1700gl_dead.fits", 
                "interactive/test_data/s7g1700ql_dead.fits"]) 
        response = self.client.post("/submit/mapping/", {
            "observatory" : "hst",
            "submitted_file" : open("interactive/test_data/hst_cos_deadtab.rmap"),
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "creator" : "Somebody else",
            })
        self.assert_no_errors(response)
        self.assertIn("hst_cos_deadtab_0001.rmap", response.content)
    
    def test_blacklist_get(self):
        self.authenticate()
        response = self.client.get("/blacklist/")
        self.assert_no_errors(response)

    def test_blacklist_post(self):
        self.fake_database_files([
                "hst_acs.imap", 
                "hst_acs_biasfile.rmap"]) 
        self.authenticate()
        response = self.client.post("/blacklist/", {
            "observatory" : "hst",
            "file_known" : "hst_acs_biasfile.rmap",
            "badflag" : "bad",
            "why" : "just had a feeling.",
            })
        # print response.content
        self.assert_no_errors(response)
        self.assertTrue("hst.pmap" in response.content)
        self.assertTrue("hst_acs.imap" in response.content)

    def test_certify_get(self):
        self.authenticate()
        response = self.client.get("/certify/")
        self.assert_no_errors(response)

    def test_certify_post_fits_uploaded(self):
        self.authenticate()
        self.fake_database_files(["interactive/test_data/s7g1700gl_dead.fits"])
        response = self.client.post("/certify/", {
            "filemode" : "file_uploaded",
            "file_uploaded" : open("interactive/test_data/s7g1700gl_dead.fits"),
        })
        self.assert_no_errors(response)
        self.assertIn("0 errors", response.content)
        self.assertEqual(response.content.count("OK"), 3)

    def test_certify_post_rmap_known(self):
        self.authenticate()
        self.fake_database_files(["hst_cos_deadtab.rmap"])
        response = self.client.post("/certify/", {
            "filemode" : "file_known",
            "file_known" : "hst_cos_deadtab.rmap",
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
        self.fake_database_files(["hst_acs.imap", "hst_cos.imap"])
        response = self.client.post("/difference/", {
            "filemode1": "file_known1",
            "file_known1" : "hst_acs.imap",
            "filemode2": "file_known2",
            "file_known2" : "hst_cos.imap"
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

    def test_create_contexts_post(self):
        self.authenticate()
        self.fake_database_files(["hst_acs_biasfile.rmap",
                                  "hst_cos_deadtab.rmap"])
        response = self.client.post("/create_contexts/", {
                "pmap_mode" : "pmap_text",
                "pmap_text" : "hst.pmap",
                "rmaps" : "hst_acs_biasfile.rmap, hst_cos_deadtab.rmap",
                "description" : "updated ACS biasfile and COS deadtab rmaps"
            })
        self.assert_no_errors(response)
        self.assertTrue("hst_0001.pmap" in response.content)
        self.assertTrue("hst_acs_0001.imap" in response.content)
        self.assertTrue("hst_cos_0001.imap" in response.content)
    
    def test_browse_file(self):
        response = self.client.get("/browse/hst.pmap")
        self.assert_no_errors(response)

    def test_browse_db_get(self):
        self.authenticate()
        response = self.client.get("/browse_db/")
        self.assert_no_errors(response)

    def test_browse_db_post(self):
        self.authenticate()
        response = self.client.post("/browse_db/", {
                "observatory" : "hst",
                "instrument" : "*",
                "filekind" : "*",
                "extension": "*",
                "filename": "hst.pmap",
                "deliverer_user": "*",
                "status":"*",
            })
        # print response
        self.assert_no_errors(response)
        self.assertTrue('hst.pmap' in response.content)
        self.assertEqual(response.content.count("<tr>"), 4)
        
    def test_edit_rmap_insert(self):
        pass

    def test_edit_rmap_replace(self):
        pass
    
    def test_batch_submit_insert(self):
        pass

    def test_batch_submit_replace(self):
        pass

