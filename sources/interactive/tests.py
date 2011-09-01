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

    def tearDown(self):
        self.del_maps(["hst_0001.pmap",
                       "hst_cos_0001.imap",
                       "hst_acs_0001.imap",
                       "hst_acs_biasfile_0001.rmap",
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

    def fake_database_files(self, files, observatory="hst"):
        for filename in files:
            models.add_crds_file(
                observatory, filename, rmap.locate_file(observatory, filename), 
                "homer", "homer@simpsons.com", "marge", "delivered by the man",
                "mass import", add_slow_fields=False)

    def test_index(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

#    def test_login(self):
#        response = self.client.post("/login/", 
#                {"username":"you", "password":"lemme guess"})
#        self.assertEqual(response.status_code, 200)
    
    def test_logout(self):
        response = self.client.get("/logout/") 
        self.assertEqual(response.status_code, 200)
    
    def test_bestrefs_index(self):
        response = self.client.get("/bestrefs/")
        self.assertEqual(response.status_code, 200)
    
    def test_bestrefs_input(self):
        response = self.client.post("/bestrefs/input/", {
            "instrument-context":"hst_acs.imap",
            })  
        self.assertEqual(response.status_code, 200)
    
    def test_bestrefs_compute(self):
        response = self.client.post("/bestrefs/compute/", {
            "instrument-context":"hst_acs.imap",
            "CCDAMP" : "ABCD",
            "CCDGAIN" : "0.0",
            "DETECTOR" : "HRC",
            "FILTER1" : "CLEAR1S",
            "FILTER2" : "CLEAR2S",
            "FW1OFFST" : "-1.0",
            "FW2OFFST" : "-1.0",
            "FWSOFFST" : "0.0",
            "LTV1" : "*",
            "LTV2" : "*",
            "NAXIS1" : "*",
            "NAXIS2" : "*",
            "OBSTYPE" : "IMAGING",
            "DATE-OBS" : "1-1-2011",
            "TIME-OBS" : "12:00:00",
        }) 
        self.assertEqual(response.status_code, 200)
    
    def test_submit_get(self):
        self.authenticate()
        response = self.client.get("/submit/")
        self.assertEqual(response.status_code, 200)

    def test_submit_input(self):
        self.authenticate()
        response = self.client.post("/submit/", {
            "observatory" : "hst",
            "filename" : "interactive/hst2.pmap",
            "modifier_name" : "zaphod",
            "description" : "an identical pmap with a different name is still different"
            })
        self.assertEqual(response.status_code, 200)
    
    def test_blacklist_get(self):
        self.authenticate()
        response = self.client.get("/blacklist/")
        self.assertEqual(response.status_code, 200)

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
        self.assertEqual(response.status_code, 200)
        # print response.content
        self.assertTrue("hst.pmap" in response.content)
        self.assertTrue("hst_acs.imap" in response.content)

    def test_using_get(self):
        response = self.client.get("/using/")
        self.assertEqual(response.status_code, 200)
    
    def test_using_post(self):
        response = self.client.post("/using/", {
                "observatory" : "hst",
                "referred_file": "v5419453j_bia.fits",
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue("hst.pmap" in response.content)
        self.assertTrue("hst_acs.imap" in response.content)
        self.assertTrue("hst_acs_biasfile.rmap" in response.content)

    def test_certify_get(self):
        self.authenticate()
        response = self.client.get("/certify/")
        self.assertEqual(response.status_code, 200)

    def test_certify_post_fits_known(self):
        self.authenticate()
        response = self.client.post("/certify/", {
            "filemode" : "file_known",
            "file_known" : "s7g1700gl_dead.fits",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.count("OK") == 2)
        self.assertTrue("0 errors" in response.content)

    def test_certify_post_rmap_known(self):
        self.authenticate()
        response = self.client.post("/certify/", {
            "filemode" : "file_known",
            "file_known" : "hst_cos_deadtab.rmap",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.count("0 errors") == 1)
        self.assertTrue("Failed" not in response.content)
        self.assertTrue(response.content.count("OK") == 2)

#    def test_certify_post_rmap_uploaded(self):
#        self.authenticate()
#        response = self.client.post("/certify/", {
#            "filemode" : "file_uploaded",
#            "file_uploaded" : "interactive/hst_cos_deadmap.rmap",
#        })
#        print response.content
#        self.assertEqual(response.status_code, 200)
#        self.assertTrue(response.content.count("0 errors") == 1)
#        self.assertTrue("Failed" not in response.content)
#        self.assertTrue(response.content.count("OK") == 2)

    def test_difference_get(self):
        response = self.client.get("/difference/")
        self.assertEqual(response.status_code, 200)

    def test_difference_post(self):
        response = self.client.post("/difference/", {
            "filemode1": "file_known1",
            "file_known1" : "hst_acs.imap",
            "filemode2": "file_known2",
            "file_known2" : "hst_cos.imap"
        })
        self.assertEqual(response.status_code, 200)
    
    def test_reserve_name_get(self):
        self.authenticate()
        response = self.client.get("/reserve_name/")
        self.assertEqual(response.status_code, 200)
    
    def test_reserve_name_post_known(self):
        self.authenticate()
        response = self.client.post("/reserve_name/", {
                "observatory" : "hst",
                "filemode" : "file_known",
                "file_known" : "hst.pmap"
            })
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 200)
        self.assertTrue("hst_acs_biasfile_0001.rmap" in response.content)


    def test_recent_activity_get(self):
        self.authenticate()
        response = self.client.get("/recent_activity/")
        self.assertEqual(response.status_code, 200)

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
        self.assertEqual(response.status_code, 200)

    def test_common_updates(self):
        self.authenticate()
        response = self.client.get("/common_updates/")
        self.assertEqual(response.status_code, 200)
    
    def test_create_contexts(self):
        self.authenticate()
        response = self.client.get("/create_contexts/")
        self.assertEqual(response.status_code, 200)

    def test_create_contexts_post(self):
        self.authenticate()
        self.fake_database_files(["hst.pmap", "hst_acs_biasfile.rmap",
                                 "hst_cos_deadtab.rmap"])
        response = self.client.post("/create_contexts/", {
                "pipeline" : "hst.pmap",
                "rmaps" : "hst_acs_biasfile.rmap, hst_cos_deadtab.rmap",
                "description" : "updated ACS biasfile and COS deadtab rmaps"
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue("hst_0001.pmap" in response.content)
        self.assertTrue("hst_acs_0001.imap" in response.content)
        self.assertTrue("hst_cos_0001.imap" in response.content)
    
    def test_replace_reference(self):
        self.authenticate()
        response = self.client.get("/replace_reference/")
        self.assertEqual(response.status_code, 200)

    def test_replace_reference_post(self):
        self.authenticate()
        self.fake_database_files([
            "hst_acs_biasfile.rmap", 
            "t4o1454bj_bia.fits", 
            "t4o1454jj_bia.fits",
            ])
        response = self.client.post("/replace_reference/", {
                "old_mapping" : "hst_acs_biasfile.rmap",
                "old_reference" : "t4o1454bj_bia.fits",
                "new_reference" : "t4o1454jj_bia.fits",
                "description" : "test reference replacement",
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue("Created" in response.content)
        self.assertTrue("hst_acs_biasfile_0001.rmap" in response.content)

    def test_browse(self):
        response = self.client.get("/browse/")
        self.assertEqual(response.status_code, 200)

    def test_browse_file(self):
        self.fake_database_files([
            "hst.pmap", 
            ])
        response = self.client.get("/browse/hst.pmap")
        self.assertEqual(response.status_code, 200)

    def test_browse_db_get(self):
        self.authenticate()
        response = self.client.get("/browse_db/")
        self.assertEqual(response.status_code, 200)

    def test_browse_db_post(self):
        self.authenticate()
        response = self.client.post("/browse_db/", {
                "observatory" : "hst",
                "instrument" : "*",
                "filekind" : "*",
                "extension": "*",
                "filename": "hst.pmap",
                "user": "*",
                "status":"*",
            })
        self.assertEqual(response.status_code, 200)
        self.assertTrue('hst.pmap' in response.content)
        self.assertEqual(response.content.count("<tr>"), 4)

