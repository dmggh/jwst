"""Unit tests to exercise the interactive portions of the CRDS server.
"""
import os
import shutil

from django.test import TestCase

from crds import (rmap, utils, pysh, log)
import crds.config as lconfig

import crds.server.interactive.models as models
import crds.server.generic_config as sconfig

from django.contrib.auth.models import User

class InteractiveBase(object):

    @classmethod
    def setUpClass(cls, *args, **keys):
        
        log.info("Setting up tests:", cls.__name__)
                
        # The results of locate_file will change when CRDS_PATH is redefined below.  Remember the real one here.
        REAL_MAPPING_DIR = os.path.dirname(rmap.locate_file("foo.pmap", sconfig.observatory))
        cached_pmap = rmap.get_cached_mapping(cls.pmap)        
        
        # Set up test server tree
        CRDS_PATH = os.environ["CRDS_PATH"] = sconfig.install_root + "/test"
        log.info("Test CRDS_PATH", CRDS_PATH, os.environ["CRDS_PATH"])

        pysh.sh("rm -rf ${CRDS_PATH}", raise_on_error=True)  #, trace_commands=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/ingest", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/deliveries", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/catalogs", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/references/%s" % sconfig.observatory, raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/mappings/%s" % sconfig.observatory, raise_on_error=True)
        for map in cached_pmap.mapping_names():
            pysh.sh("cp ${REAL_MAPPING_DIR}/${map} ${CRDS_PATH}/mappings/%s" % sconfig.observatory, raise_on_error=True)
        # monkey-patch these since they're not encapsulated with functions.
        sconfig.CRDS_INGEST_DIR = os.path.join(CRDS_PATH, "ingest")
        sconfig.CRDS_DELIVERY_DIR = os.path.join(CRDS_PATH, "deliveries")
        sconfig.CRDS_DELIVERY_DIRS = [os.path.join(CRDS_PATH, "deliveries")]
        sconfig.CRDS_CATALOG_DIR = os.path.join(CRDS_PATH, "catalogs")
        sconfig.FILE_UPLOAD_TEMP_DIR = os.path.join(CRDS_PATH, "uploads")

    @classmethod
    def tearDownClass(self):
        os.environ["CRDS_PATH"] = sconfig.install_root
        
    def runTest(self, *args, **keys):
        pass
    
    def setUp(self): 
        self.user = User.objects.create_user('homer', 'homer@simpson.net', 'simpson')
        try:
            self.user.save()    
        except Exception, exc:
            print "failed user save:", str(exc)
        self.ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, str(self.user))
        self.fake_database_files([self.pmap])
        models.set_default_context(self.pmap)
        models.set_default_context(self.pmap, state="operational")
        utils.ensure_dir_exists(lconfig.get_crds_refpath())
        utils.ensure_dir_exists(lconfig.get_crds_mappath())
        self.ingested = False
        
    def tearDown(self):
        self.del_maps(self.delete_files)
        pysh.sh("/bin/rm -rf " + lconfig.get_crds_refpath(), raise_on_error=True)  # , trace_commands=True)
        if self.ingested:
            pysh.sh("/bin/rm -rf " + self.ingest_path, raise_on_error=True) # , trace_commands=True)

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
        self.assertNotIn("ERROR", response.content)
        self.assertNotIn("Error", response.content)
        
    def assert_has_error(self, response, msg=None):
        self.assertEqual(response.status_code, 200)
        self.assertIn("ERROR", response.content)
        if msg is not None:
            self.assertIn(msg, response.content)

    def test_index(self):
        response = self.client.get('/')
        self.assert_no_errors(response)

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
            dataset1 = "interactive/test_data/jw00001001001_01101_00001_MIRIMAGE_uncal.fits"
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
        self.fake_database_files(self.submit_references)
        self.add_file_to_ingest_dir(self.submit_rmap)
        rmap2 = self.add_1(self.submit_rmap)
        response = self.client.post("/submit/mapping/", {
            "observatory" : sconfig.observatory,
            "auto_rename" : "on",
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "creator" : "Somebody else",
            "pmap_mode" : "pmap_edit",
            }, follow=True)
        self.assert_no_errors(response)
        self.assertIn(rmap2, response.content)
        
    def add_files_to_ingest_dir(self, filepaths):
        for path in filepaths:
            self.add_file_to_ingest_dir(path)
        
    def add_file_to_ingest_dir(self, filepath):
        self.ingested = True
        ingest_file = os.path.join(self.ingest_path, os.path.basename(filepath))
        utils.ensure_dir_exists(ingest_file)
        try:
            log.info("linking ingest", ingest_file, "to", filepath)
            shutil.copy(filepath, ingest_file)
            os.chmod(ingest_file, 0666)
        except Exception, exc:
            log.info("failed to add file:", str(exc))
        
    def test_set_file_enable_get(self):
        self.authenticate()
        response = self.client.get("/set_file_enable/")
        self.assert_no_errors(response)

    def test_set_file_enable_blacklist_post(self):
        self.authenticate()
        self.fake_database_files(self.blacklist_files)
        response = self.client.post("/set_file_enable/", {
            "observatory" : sconfig.observatory,
            "file_known" : self.blacklist_files[1],
            "badflag" : "bad",
            "reject_type" : "blacklist",
            "why" : "just had a feeling.",
            })
        # print response.content
        imap, rmap = self.blacklist_files
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
        self.authenticate()
        self.fake_database_files(self.blacklist_files)
        response = self.client.post("/set_file_enable/", {
            "observatory" : sconfig.observatory,
            "file_known" : self.blacklist_files[1],
            "badflag" : "bad",
            "reject_type" : "reject",
            "why" : "just had a feeling.",
            })
        # print response.content
        imap, rmap = self.blacklist_files
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
        self.fake_database_files([self.certify_post_fits])
        self.add_file_to_ingest_dir(self.certify_post_fits)
        response = self.client.post("/certify/", {
            "pmap_mode": "pmap_edit",
        })
        # print "certify post FITS response:", response.content
        self.assert_no_errors(response)
        self.assertNotIn("ERROR", response.content)
        self.assertEqual(response.content.count("OK"), 1)

    def test_certify_post_rmap_uploaded(self):
        self.authenticate()
        self.add_file_to_ingest_dir(self.certify_rmap)
        self.fake_database_files(self.certify_rmap_fits)
        response = self.client.post("/certify/", {
            "pmap_mode": "pmap_edit",
        })
        self.assert_no_errors(response)
        self.assertTrue("ERROR", response.content)
        self.assertTrue("Failed" not in response.content)
        self.assertTrue(response.content.count("OK") == 1)

    def test_difference_get(self):
        response = self.client.get("/difference/")
        self.assert_no_errors(response)

    def test_difference_post(self):
        self.fake_database_files(self.difference_files)
        response = self.client.post("/difference/", {
            "filemode1": "file_known1",
            "file_known1" : self.difference_files[0],
            "filemode2": "file_known2",
            "file_known2" : self.difference_files[1],
        })
        self.assert_no_errors(response)
    
    def test_difference_post_uploaded(self):
        self.fake_database_files(self.difference_files)
        response = self.client.post("/difference/", {
            "filemode1": "file_uploaded2",
            "file_uploaded1" : open(self.difference_files_uploaded[0]),
            "filemode2": "file_uploaded2",
            "file_uploaded2" : open(self.difference_files_uploaded[1]),
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
        self.fake_database_files(self.create_contexts_rmaps)
        response = self.client.post("/create_contexts/", {
                "pmap_mode" : "pmap_text",
                "pmap_text" : self.pmap,
                "rmaps" : " ".join(self.create_contexts_rmaps),
                "description" : "updated rmaps"
            }, follow=True)
        rmap1, rmap2 = self.create_contexts_rmaps
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
        self.add_files_to_ingest_dir(self.batch_submit_replace_references)
        response = self.client.post("/batch_submit_references/", {
                "pmap_mode" : "pmap_edit",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "description":"this is only a test.",
            }, follow=True)
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Cancel", response.content)
        self.assertIn("replace", response.content)
        self.assertNotIn("insert", response.content)
        self.assertIn("Reversion at", response.content)

    def _batch_submit_insert(self, references=None):
        self.authenticate()
        if references is None:
            references = self.batch_submit_insert_references
        self.add_files_to_ingest_dir(references)
        response = self.client.post("/batch_submit_references/", {
                "pmap_mode" : "pmap_edit",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "description":"this is only a test.",
                "auto_rename" : "checked",
            }, follow=True)
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Cancel", response.content)
        self.assertIn("added", response.content)
        self.assertNotIn("replace", response.content)
    
    def test_batch_submit_insert(self):
        self._batch_submit_insert()
        
    def _confirm(self):
        pass
    
    def _cancel(self):
        pass
    
    def test_batch_submit_confirm(self):
        self._batch_submit_insert()
        self._confirm()
        
    def test_batch_submit_cancel(self):
        self._batch_submit_insert()
        self._cancel()
      
    def test_get(self):
        pass

if sconfig.observatory == "hst":
    
    class HstInteractiveTest(InteractiveBase, TestCase):
        
        pmap = "hst.pmap"
        
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

        rmap1 = "interactive/test_data/hst_cos_deadtab.rmap"

        difference_files = ["hst_acs.imap", "hst_cos.imap"]
        difference_files_uploaded = ["interactive/test_data/hst_acs.imap", 
                                     "interactive/test_data/hst_cos.imap"]

        certify_rmap = "interactive/test_data/hst_cos_deadtab.rmap"
        certify_rmap_fits = ["s7g1700ql_dead.fits", "s7g1700gl_dead.fits"]

        certify_post_fits = "interactive/test_data/s7g1700gl_dead.fits"
        
        submit_rmap = "interactive/test_data/hst_cos_deadtab.rmap"
        submit_references = [
                "interactive/test_data/s7g1700gl_dead.fits", 
                "interactive/test_data/s7g1700ql_dead.fits"
        ]         

        batch_submit_replace_references = ["interactive/test_data/s7g1700gl_dead.fits",
                                           "interactive/test_data/aaaa.fits"]
        batch_submit_insert_references = ["interactive/test_data/s7g1700gm_dead.fits"]
        
        create_contexts_rmaps = ["hst_acs_biasfile.rmap", "hst_cos_deadtab.rmap"]

        blacklist_files = ["hst_acs.imap", "hst_acs_biasfile.rmap"]           

else:  # JWST
    
    class JwstInteractiveTest(InteractiveBase, TestCase):

        pmap = "jwst_0000.pmap"
        
        delete_files = [
            "jwst_0001.pmap",
            "jwst_miri_0001.imap",
            "jwst_nircam_0001.imap",
            "jwst_miri_flat_0001.rmap",
            "jwst_miri_amplifier_0001.rmap",
            "jwst_miri_photom_0001.rmap",
        ]

        difference_files = ["jwst_miri_0000.imap", 
                            "jwst_nircam_0000.imap"]

        difference_files_uploaded = ["interactive/test_data/jwst_miri_0000.imap", 
                                     "interactive/test_data/jwst_nircam_0000.imap"]

        certify_rmap = "interactive/test_data/jwst_miri_amplifier_0000.rmap"
        certify_rmap_fits = ["jwst_miri_amplifier_0000.fits",
                             "jwst_miri_amplifier_0001.fits",
                             "jwst_miri_amplifier_0002.fits"]
        certify_post_fits = "interactive/test_data/jwst_miri_photom_0001.fits"

        submit_rmap = "interactive/test_data/jwst_miri_amplifier_9999.rmap"
        submit_references = ["jwst_miri_amplifier_0000.fits",
                             "jwst_miri_amplifier_0001.fits",
                             "jwst_miri_amplifier_0002.fits"]

        batch_submit_replace_references = ["interactive/test_data/jwst_miri_amplifier_0000.fits",
                                           "interactive/test_data/jwst_miri_photom_9999.fits"]
        batch_submit_insert_references = ["interactive/test_data/jwst_miri_amplifier_9998.fits",
                                          "interactive/test_data/jwst_miri_photom_9998.fits"]
        
        create_contexts_rmaps = ["jwst_miri_amplifier_0000.rmap", 
                                 "jwst_miri_photom_0000.rmap"]

        blacklist_files = ["jwst_miri_0000.imap", "jwst_miri_photom_0000.rmap"]

