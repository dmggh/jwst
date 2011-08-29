"""Unit tests to exercise the interactive portions of the CRDS server.
"""

from django.test import TestCase

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

    def authenticate(self):
        login = self.client.login(username="homer", password="simpson")
        self.assertTrue(login)
    
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
        self.authenticate()
        response = self.client.post("/blacklist/", {
            "observatory" : "hst",
            "file_known" : "hst_acs_biasfile.rmap",
            "badflag" : "bad",
            "why" : "just had a feeling.",
            })
        self.assertEqual(response.status_code, 200)
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

    def test_certify_post_fits(self):
        self.authenticate()
        response = self.client.post("/certify/", {
            "filemode" : "file_known",
            "file_known" : "s7g1700gl_dead.fits",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.count("OK") == 2)
        self.assertTrue("0 errors" in response.content)

    def test_certify_post_rmap(self):
        self.authenticate()
        response = self.client.post("/certify/", {
            "filemode" : "file_known",
            "file_known" : "hst_cos_deadtab.rmap",
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.count("0 errors") == 2)
        self.assertTrue("Failed" not in response.content)
        self.assertTrue(response.content.count("OK") == 3)

"""
    def test_difference(self):
        self.assertTrue(False)
    
    def test_reserve_name(self):
        self.assertTrue(False)
    
    def test_recent_activity(self):
        self.assertTrue(False)
    
    def test_common_updates(self):
        self.assertTrue(False)
    
    def test_create_contexts(self):
        self.assertTrue(False)
    
    def test_browse(self):
        self.assertTrue(False)

    def test_browse_file(self):
        self.assertTrue(False)

"""
