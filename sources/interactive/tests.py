"""Unit tests to exercise the interactive portions of the CRDS server.
"""
import os

from django.test import TestCase

import crds.rmap as rmap
import crds.server.interactive.models as models

"""
  url(r'^$', 'crds.server.interactive.views.index'),          

  url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),          
  url(r'^logout/$', 'crds.server.interactive.views.logout'),          

  url(r'^bestrefs/$', 'crds.server.interactive.views.bestrefs_index'),          
  url(r'^bestrefs/input/$', 'crds.server.interactive.views.bestrefs_input'),          
  url(r'^bestrefs/compute/$', 'crds.server.interactive.views.bestrefs_compute'),

  url(r'^submit/$',       'crds.server.interactive.views.submit_file'),          
  url(r'^blacklist/$',    'crds.server.interactive.views.blacklist_file'),          
  url(r'^using/$',        'crds.server.interactive.views.using_file'),          
  url(r'^certify/$',      'crds.server.interactive.views.certify_file'),          
  url(r'^difference/$',   'crds.server.interactive.views.difference_files'),
  url(r'^reserve_name/$', 'crds.server.interactive.views.reserve_name'),        
  url(r'^recent_activity/$', 'crds.server.interactive.views.recent_activity'),        

  url(r'^common_updates/$', 'crds.server.interactive.views.common_updates'),        
  url(r'^create_contexts/$', 'crds.server.interactive.views.create_contexts'),        
          
  url(r'^browse/$', 'crds.server.interactive.views.browse_files'),        
  url(r'^browse/(?P<original_name>[A-Za-z0-9_.]+(fits|imap|rmap|pmap))$', 
      'crds.server.interactive.views.browse_known_file'),
"""

from django.contrib.auth.models import User

class SimpleTest(TestCase):
    def setUp(self): 
        User.objects.create_user('homer', 'ho...@simpson.net', 'simpson')     
        index = models.create_index("hst")
        index.save()

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
            location = filename if os.path.dirname(filename) else rmap.locate_file(filename)
            models.add_crds_file(
                observatory, name, location, 
                deliverer="homer", deliverer_email="homer@simpsons.com", 
                description="delivered by the man",
                creation_method="mass import", add_slow_fields=False)

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
        self.fake_database_files(["hst.pmap"])
        response = self.client.post("/bestrefs/", {
            "context_mode" : "context_user",
            "context_user" : "hst.pmap",
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
        response = self.client.post("/reserve_name/", {
                "observatory" : "hst",
                "filemode" : "file_known",
                "file_known" : "hst_cos_deadtab_0001.rmap"
            })
        self.assert_no_errors(response)
        self.assertIn("hst_cos_deadtab_0001.rmap", response.content)
        response = self.client.post("/submit/mapping/", {
            "observatory" : "hst",
            "comparison_file" : "",
            "submitted_file" : open("interactive/test_data/hst_cos_deadtab_0001.rmap"),
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "opus_flag" : "Y",
            })
        self.assert_no_errors(response)
        self.assertIn("hst_cos_deadtab_0001.rmap", response.content)
    
    def test_blacklist_get(self):
        self.authenticate()
        response = self.client.get("/blacklist/")
        self.assert_no_errors(response)

    def test_blacklist_post(self):
        # Make database entries for files we know will be blacklisted
        self.fake_database_files([
                "hst.pmap", "hst_acs.imap", "hst_acs_biasfile.rmap"]) 
        self.authenticate()
        response = self.client.post("/blacklist/", {
            "observatory" : "hst",
            "file_known" : "hst_acs_biasfile.rmap",
            "badflag" : "bad",
            "why" : "just had a feeling.",
            })
        self.assert_no_errors(response)
        # print response.content
        self.assertTrue("hst.pmap" in response.content)
        self.assertTrue("hst_acs.imap" in response.content)

    def test_using_get(self):
        response = self.client.get("/using/")
        self.assert_no_errors(response)
    
    def test_using_post(self):
        self.fake_database_files(["interactive/test_data/t4o1454bj_bia.fits"])
        response = self.client.post("/using/", {
                "observatory" : "hst",
                "referred_file": "t4o1454bj_bia.fits",
            })
        self.assert_no_errors(response)
        self.assertTrue("hst.pmap" in response.content)
        self.assertTrue("hst_acs.imap" in response.content)
        self.assertTrue("hst_acs_biasfile.rmap" in response.content)

    def test_matches_get(self):
        response = self.client.get("/matches/")
        self.assert_no_errors(response)
    
    def test_matches_post(self):
        self.fake_database_files([
                "hst_acs_biasfile.rmap",
                "interactive/test_data/t4o1454bj_bia.fits"
            ])
        response = self.client.post("/matches/", {
                "known_context" : "hst_acs_biasfile.rmap",
                "matched_reference": "t4o1454bj_bia.fits",
            })
        self.assert_no_errors(response)
        self.assertTrue("INSTRUME" in response.content)
        self.assertTrue("DETECTOR" in response.content)
        self.assertTrue("success" in response.content)

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
        self.assertEqual(response.content.count("OK"), 3)
        self.assertIn("0 errors", response.content)

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
    
    def test_reserve_name_get(self):
        self.authenticate()
        response = self.client.get("/reserve_name/")
        self.assert_no_errors(response)
    
    def test_reserve_name_post_known(self):
        self.authenticate()
        response = self.client.post("/reserve_name/", {
                "observatory" : "hst",
                "filemode" : "file_known",
                "file_known" : "hst_0001.pmap"
            })
        self.assert_no_errors(response)
        self.assertTrue("hst_0001.pmap" in response.content)

    def test_reserve_name_post_parts(self):
        self.authenticate()
        response = self.client.post("/reserve_name/", {
                "observatory" : "hst",
                "instrument" : "acs",
                "filekind" : "biasfile",
                "extension" : ".rmap",
                "filemode" : "by_parts",
                "file_known" : "hst.pmap"
            })
        self.assert_no_errors(response)
        self.assertTrue("hst_acs_biasfile_0001.rmap" in response.content)


    def test_recent_activity_get(self):
        self.authenticate()
        response = self.client.get("/recent_activity/")
        self.assert_no_errors(response)

    def test_recent_activity_post(self):
        self.authenticate()
        response = self.client.post("/recent_activity/", {
                "action" : "reserve name",
                "observatory" : "*",
                "instrument" : "*",
                "filekind" : "*",
                "extension" : "*",
                "filename" : "*",
                "user" : "*",
            })
        self.assert_no_errors(response)

    def test_common_updates(self):
        self.authenticate()
        response = self.client.get("/common_updates/")
        self.assert_no_errors(response)
    
    def test_create_contexts(self):
        self.authenticate()
        response = self.client.get("/create_contexts/")
        self.assert_no_errors(response)

    def test_create_contexts_post(self):
        self.authenticate()
        self.fake_database_files(["hst.pmap", "hst_acs_biasfile.rmap",
                                 "hst_cos_deadtab.rmap"])
        response = self.client.post("/create_contexts/", {
                "pipeline" : "hst.pmap",
                "rmaps" : "hst_acs_biasfile.rmap, hst_cos_deadtab.rmap",
                "description" : "updated ACS biasfile and COS deadtab rmaps"
            })
        self.assert_no_errors(response)
        self.assertTrue("hst_0001.pmap" in response.content)
        self.assertTrue("hst_acs_0001.imap" in response.content)
        self.assertTrue("hst_cos_0001.imap" in response.content)
    
    def test_replace_reference(self):
        self.authenticate()
        response = self.client.get("/replace_reference/")
        self.assert_no_errors(response)

    def test_replace_reference_post(self):
        self.authenticate()
        self.fake_database_files([
            "hst_acs_biasfile.rmap", 
            "interactive/test_data/t4o1454bj_bia.fits", 
            "interactive/test_data/t4o1454jj_bia.fits",
            ])
        response = self.client.post("/replace_reference/", {
                "old_mapping" : "hst_acs_biasfile.rmap",
                "old_reference" : "t4o1454bj_bia.fits",
                "new_reference" : "t4o1454jj_bia.fits",
                "description" : "test reference replacement",
            })
        self.assert_no_errors(response)
        self.assertTrue("Created" in response.content)
        self.assertTrue("hst_acs_biasfile_0001.rmap" in response.content)

    def test_add_useafter(self):
        self.authenticate()
        response = self.client.get("/add_useafter/")
        self.assert_no_errors(response)

    def test_add_useafter_post_insert(self):
        self.authenticate()
        self.fake_database_files([
            "hst_acs_dgeofile.rmap", 
            "interactive/test_data/o8u2214fj_dxy.fits", 
            ])
        response = self.client.post("/add_useafter/", {
                "old_mapping" : "hst_acs_dgeofile.rmap",
                "match_tuple" : "('HRC', 'CLEAR1S', 'F220W')",
                "useafter_date" : "2001-01-27 12:00:09",
                "useafter_file" : "o8u2214fj_dxy.fits",
                "description" : "test add useafter",
            })
        self.assert_no_errors(response)
        self.assertTrue("Created" in response.content)
        self.assertTrue("Inserted useafter into existing match case." in response.content)

    def test_add_useafter_post_append(self):
        self.authenticate()
        self.fake_database_files([
            "hst_acs_dgeofile.rmap", 
            "interactive/test_data/o8u2214fj_dxy.fits", 
            ])
        response = self.client.post("/add_useafter/", {
                "old_mapping" : "hst_acs_dgeofile.rmap",
                "match_tuple" : "('HRC', 'CLEAR1S', 'F220W')",
                "useafter_date" : "2012-01-27 00:00:00",
                "useafter_file" : "o8u2214fj_dxy.fits",
                "description" : "test add useafter",
            })
        self.assert_no_errors(response)
        self.assertTrue("Created" in response.content)
        self.assertTrue("Appended useafter to existing match case." in response.content)

    def test_add_useafter_post_nomatch(self):
        self.authenticate()
        self.fake_database_files([
            "hst_acs_dgeofile.rmap", 
            "interactive/test_data/o8u2214fj_dxy.fits", 
            ])
        response = self.client.post("/add_useafter/", {
                "old_mapping" : "hst_acs_dgeofile.rmap",
                "match_tuple" : "('HRC', 'CLEAR1S', 'F220Q')",  #Q made up!!!
                "useafter_date" : "2012-01-27 00:00:00",
                "useafter_file" : "o8u2214fj_dxy.fits",
                "description" : "test add useafter",
            })
        self.assert_has_error(response, "Couldn&#39;t find match tuple")

    def test_browse(self):
        response = self.client.get("/browse/")
        self.assert_no_errors(response)

    def test_browse_file(self):
        self.fake_database_files([
            "hst.pmap", 
            ])
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
        self.assert_no_errors(response)
        self.assertTrue('hst.pmap' in response.content)
        self.assertEqual(response.content.count("<tr>"), 4)

