"""Unit tests to exercise the interactive portions of the CRDS server.
"""
import os

from django.test import TestCase

from crds import (rmap, utils, pysh)
import crds.config as lconfig

import crds.server.interactive.models as models
import crds.server.config as sconfig

from django.contrib.auth.models import User

REAL_MAPPING_DIR = os.path.dirname(rmap.locate_file("foo.pmap", sconfig.observatory))

# Set up test server tree
HERE = os.path.dirname(__file__) or "."
CRDS_PATH = os.environ["CRDS_PATH"] = sconfig.install_root + "/test"
pysh.sh("rm -rf ${CRDS_PATH}", raise_on_error=True)
pysh.sh("mkdir -p ${CRDS_PATH}/ingest", raise_on_error=True)
pysh.sh("mkdir -p ${CRDS_PATH}/deliveries", raise_on_error=True)
pysh.sh("mkdir -p ${CRDS_PATH}/catalogs", raise_on_error=True)
pysh.sh("mkdir -p ${CRDS_PATH}/references/%s" % sconfig.observatory, raise_on_error=True)
pysh.sh("mkdir -p ${CRDS_PATH}/mappings/%s" % sconfig.observatory, raise_on_error=True)
pysh.sh("cp ${REAL_MAPPING_DIR}/*.*map ${CRDS_PATH}/mappings/%s" % sconfig.observatory, raise_on_error=True)



class SimpleTest(TestCase):
    
    def runTest(self, *args, **keys):
        pass
    
    pmap = sconfig.observatory + ".pmap"
    
    def setUp(self): 
        User.objects.create_user('homer', 'homer@simpson.net', 'simpson')     
        self.fake_database_files([self.pmap])
        models.set_default_context(self.pmap)
        models.set_default_context(self.pmap, state="operational")
        utils.ensure_dir_exists(lconfig.get_crds_refpath())
        utils.ensure_dir_exists(lconfig.get_crds_mappath())
        
    def tearDown(self):
        if sconfig.observatory == "hst":
            delete_files = [
                "hst_0001.pmap",
                "hst_0002.pmap",
                "hst_0003.pmap",
                "hst_cos_0001.imap",
                "hst_acs_0001.imap",
                "hst_acs_0002.imap",
                "hst_acs_0003.imap",
                "hst_cos_deadtab_0001.rmap",
                "hst_acs_biasfile_0001.rmap",
                "hst_acs_dgeofile_0001.rmap",
                "hst_acs_darkfile_0001.rmap",
                ]
        else:
            delete_files = [
                "jwst_0001.pmap",
                "jwst_miri_0001.imap",
                "jwst_nircam_0001.imap",
                "jwst_miri_flat_0001.rmap",
                "jwst_nircam_flat_0001.rmap",
                ]
        self.del_maps(delete_files)
        pysh.sh("/bin/rm -rf " + lconfig.get_crds_refpath(), 
                    raise_on_error=True,
                ) # trace_commands=True)

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

    def assert_no_errors(self, response, status=200):
        self.assertEqual(response.status_code, status)
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
        self.assert_no_errors(response, status=302) #redirect
    
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
            rmap1 = "interactive/test_data/jwst_miri_flat.rmap"
            self.fake_database_files([
                "interactive/test_data/jwst_miri_flat_0001.fits",])
        rmap2 = self.add_1(rmap1)
        response = self.client.post("/submit/mapping/", {
            "observatory" : sconfig.observatory,
            "auto_rename" : "on",
            "file_mode" : "file_uploaded",
            "file_uploaded" : open(rmap1),
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "creator" : "Somebody else",
            })
        self.assert_no_errors(response)
        self.assertIn(rmap2, response.content)
    
    def test_set_file_enable_get(self):
        self.authenticate()
        response = self.client.get("/set_file_enable/")
        self.assert_no_errors(response)

    def test_set_file_enable_blacklist_post(self):
        if sconfig.observatory == "hst":
            imap = "hst_acs.imap"
            rmap = "hst_acs_biasfile.rmap"            
        else:
            imap = "jwst_miri.imap"
            rmap = "jwst_miri_flat.rmap"
        self.authenticate()
        self.fake_database_files([imap, rmap])
        response = self.client.post("/set_file_enable/", {
            "observatory" : sconfig.observatory,
            "file_known" : rmap,
            "badflag" : "bad",
            "reject_type" : "blacklist",
            "why" : "just had a feeling.",
            })
        # print response.content
        self.assert_no_errors(response)
        self.assertTrue(self.pmap in response.content)
        self.assertTrue(imap in response.content)
        self.assertTrue(rmap in response.content)
        rmapblob = models.FileBlob.load(rmap)
        imapblob = models.FileBlob.load(imap)
        self.assertTrue(rmapblob.blacklisted)
        self.assertFalse(rmapblob.rejected)
        self.assertTrue(imapblob.blacklisted)
        self.assertFalse(imapblob.rejected)

    def test_set_file_enable_reject_post(self):
        if sconfig.observatory == "hst":
            imap = "hst_acs.imap"
            rmap = "hst_acs_biasfile.rmap"            
        else:
            imap = "jwst_miri.imap"
            rmap = "jwst_miri_flat.rmap"
        self.authenticate()
        self.fake_database_files([imap, rmap])
        response = self.client.post("/set_file_enable/", {
            "observatory" : sconfig.observatory,
            "file_known" : rmap,
            "badflag" : "bad",
            "reject_type" : "reject",
            "why" : "just had a feeling.",
            })
        # print response.content
        self.assert_no_errors(response)
        self.assertTrue(self.pmap not in response.content)
        self.assertTrue(imap not in response.content)
        self.assertTrue(rmap in response.content)
        rmapblob = models.FileBlob.load(rmap)
        imapblob = models.FileBlob.load(imap)
        self.assertFalse(rmapblob.blacklisted)
        self.assertTrue(rmapblob.rejected)
        self.assertFalse(imapblob.blacklisted)
        self.assertFalse(imapblob.rejected)

    def test_certify_get(self):
        self.authenticate()
        response = self.client.get("/certify/")
        self.assert_no_errors(response)

    def test_certify_post_fits_uploaded(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            fits = "interactive/test_data/s7g1700gl_dead.fits"
        else:
            fits = "interactive/test_data/jwst_miri_fakeflat.fits"
        self.fake_database_files([fits])
        response = self.client.post("/certify/", {
            "filemode" : "file_uploaded",
            "file_uploaded" : open(fits),
        })
        self.assert_no_errors(response)
        self.assertIn("0 errors", response.content)
        self.assertEqual(response.content.count("OK"), 2)

    def test_certify_post_rmap_known(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            rmap = "hst_cos_deadtab.rmap"
        else:
            rmap = "jwst_miri_flat.rmap"
        self.fake_database_files([rmap])
        response = self.client.post("/certify/", {
            "filemode" : "file_known",
            "file_known" : rmap,
        })
        self.assert_no_errors(response)
        self.assertTrue(response.content.count("0 errors") == 1)
        self.assertNotIn("Failed", response.content)
        self.assertEqual(response.content.count("OK"), 2)

    def test_certify_post_rmap_uploaded(self):
        self.authenticate()
        response = self.client.post("/certify/", {
            "filemode" : "file_uploaded",
            "file_uploaded" : open("interactive/test_data/hst_cos_deadtab.rmap"),
        })
        self.assert_no_errors(response)
        self.assertTrue(response.content.count("0 errors") == 1)
        self.assertTrue("Failed" not in response.content)
        self.assertTrue(response.content.count("OK") == 2)

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
            rmap1 = "jwst_miri_flat.rmap"
            rmap2 = "jwst_nircam_flat.rmap"
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

    def test_batch_submit_replace(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            reference = "interactive/test_data/s7g1700gl_dead.fits"
        else:
            reference = "interactive/test_data/jwst_miri_fakeflat.fits"
        response = self.client.post("/batch_submit_reference/", {
                "pmap_mode" : "pmap_default",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "pmap_default" : self.pmap,
                "file_mode" : "file_uploaded",
                "file_uploaded" : open(reference),
                "description":"this is only a test.",
                "auto_rename" : "checked",
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
            reference = "interactive/test_data/jwst_miri_flat_insert.fits"
        response = self.client.post("/batch_submit_reference/", {
                "pmap_mode" : "pmap_default",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "pmap_default" : self.pmap,
                "file_mode" : "file_uploaded",
                "file_uploaded" : open(reference),
                "description":"this is only a test.",
            })
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Abort", response.content)
        self.assertIn("INSERT", response.content)
        self.assertNotIn("REPLACE", response.content)
        
    def test_edit_rmap_browse_get(self):
        self.authenticate()
        response = self.client.get("/edit_rmap_browse/")
        self.assert_no_errors(response)

    def test_edit_rmap_browse_post(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            instrument = "acs"
            filekind = "darkfile"
            rmap = "hst_acs_darkfile.rmap"
        else:
            instrument = "miri"
            filekind = "flat"
            rmap = "jwst_miri_flat.rmap"
        self.fake_database_files([rmap])
        response = self.client.post("/edit_rmap_browse/", {
                "observatory" : sconfig.observatory,
                "instrument" : instrument,
                "filekind": filekind,
                "extension" : "*",
                "filename" : "*",
                "deliverer_user" : "*",
                "status" : "*",
            })
        self.assert_no_errors(response)
        self.assertIn(rmap, response.content)

    def test_edit_rmap_get(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            instrument = "acs"
            filekind = "darkfile"
            rmap = "hst_acs_darkfile.rmap"
        else:
            instrument = "miri"
            filekind = "flat"
            rmap = "jwst_miri_flat.rmap"
        self.fake_database_files([rmap])
        response = self.client.get("/edit_rmap/"+rmap+"/")
        self.assertIn("Click on a useafter date to edit", response.content)

    def test_edit_rmap_insert(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            rmap = "hst_acs_darkfile.rmap"
            match_tuple = "('HRC', 'A|ABCD|AD|B|BC|C|D', '1.0|2.0|4.0|8.0')"
            reference = "interactive/test_data/n3o1059rk_drk.fits"
        else:
            instrument = "miri"
            filekind = "flat"
            rmap = "jwst_miri_flat.rmap"
            match_tuple = "()"
            reference = "interactive/test_data/jwst_miri_fakeflat.fits"
        self.fake_database_files([rmap])
        response = self.client.post("/edit_rmap/", {
            "pmap_mode" : "pmap_default",
            "pmap_default" : self.pmap,
            "description" : "Something.",
            "add.0.match_tuple" : match_tuple,
            "add.0.date" : "2002-03-24 00:34:29",
            "add.0.change_level" : "SEVERE",
            "add.0.filename" : open(reference),
            "browsed_file" : rmap,    
            "creator" : "bozo",            
            })
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Abort", response.content)
        self.assertIn("add", response.content)
        self.assertNotIn("delete", response.content)

    def test_edit_rmap_replace(self):
        self.authenticate()
        if sconfig.observatory == "hst":
            rmap = "hst_acs_darkfile.rmap"
            match_tuple = "('HRC', 'A|ABCD|AD|B|BC|C|D', '1.0|2.0|4.0|8.0')"
            add_reference = "interactive/test_data/n3o1059rk_drk.fits"
            del_reference = "n3o1022nj_drk.fits"
            date = "2002-03-24 00:34:28"
        else:
            instrument = "miri"
            filekind = "flat"
            rmap = "jwst_miri_flat.rmap"
            match_tuple = "()"
            add_reference = "interactive/test_data/jwst_miri_fakeflat.fits"
            del_reference = "jwst_miri_flat_0001.fits"
            date = "1990-01-01 00:00:00"
        self.fake_database_files([rmap, del_reference])
        response = self.client.post("/edit_rmap/", {
            "pmap_mode" : "pmap_default",
            "pmap_default" : self.pmap,
            "description" : "Something.",
            
            "add.0.match_tuple" : match_tuple,
            "delete.0.match_tuple": match_tuple,
            
            "add.0.date" : date,
            "delete.0.date" : date,
            
            "add.0.change_level" : "SEVERE",
            
            "add.0.filename" : open(add_reference),
            "delete.0.filename" : del_reference,
            
            "browsed_file" : rmap,                
            "creator" : "bozo",            
            })
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Abort", response.content)
        self.assertIn("add", response.content)
        self.assertIn("delete", response.content)
        
    def test_get(self):
        pass
    
    def test_batch_submit_server_mode(self):
        pass
    
    def test_simple_submit_server_mode(self):
        pass
    

