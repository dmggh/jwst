"""Unit tests to exercise the interactive portions of the CRDS server."""

import sys
import os
import shutil
import os.path

from django.test import TransactionTestCase, TestCase

from crds import (rmap, utils, pysh, log)
import crds.config as lconfig

from crds.server import settings
from crds.server import config as sconfig
from crds.server.interactive import models, locks

from django.contrib.auth.models import User

class InteractiveBase(object):

    @classmethod
    def setUpClass(cls, *args, **keys):
        
        log.info("Setting up tests:", cls.__name__)
                
        # The results of locate_file will change when CRDS_PATH is redefined below.
        # Remember the real one here.
        REAL_MAPPING_DIR = os.path.dirname(rmap.locate_file("foo.pmap", cls.observatory))
        cached_pmap = rmap.get_cached_mapping(cls.pmap)        
        
        # Set up test server tree
        CRDS_PATH = os.environ["CRDS_PATH"] = sconfig.install_root + "/test"
        log.info("Test CRDS_PATH", CRDS_PATH, os.environ["CRDS_PATH"])

        pysh.sh("rm -rf ${CRDS_PATH}", raise_on_error=True)  #, trace_commands=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/ingest", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/deliveries", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/catalogs", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/references/%s" % cls.observatory, raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/mappings/%s" % cls.observatory, raise_on_error=True)

        mappings = cached_pmap.mapping_names()
        for map in mappings:
            pysh.sh("cp ${REAL_MAPPING_DIR}/${map} ${CRDS_PATH}/mappings/%s" % cls.observatory, raise_on_error=True)
        cls.fake_database_files(mappings)
            
        # monkey-patch these since they're not encapsulated with functions.
        sconfig.CRDS_INGEST_DIR = os.path.join(CRDS_PATH, "ingest")
        sconfig.CRDS_DELIVERY_DIR = os.path.join(CRDS_PATH, "deliveries")
        sconfig.CRDS_DELIVERY_DIRS = [os.path.join(CRDS_PATH, "deliveries")]
        sconfig.CRDS_CATALOG_DIR = os.path.join(CRDS_PATH, "catalogs")
        sconfig.FILE_UPLOAD_TEMP_DIR = os.path.join(CRDS_PATH, "uploads")
        settings.CRDS_LOCK_ACQUIRE_TIMEOUT = 0.5  # Don't waste time during tests with SQLite

    @classmethod
    def tearDownClass(self):
        os.environ["CRDS_PATH"] = sconfig.install_root
        
    def runTest(self, *args, **keys):
        pass
    
    passwords = {
        "homer" : "simposon",
        "bozo" : "the clown",
    }
    
    def setUp(self): 
        self.user = User.objects.create_user('homer', 'homer@simpson.net', self.passwords["homer"])
        self.user2 = User.objects.create_user('bozo', 'bozo@godaddy.com', self.passwords["bozo"])
        self.user.is_superuser = True
        try:
            self.user.save() 
            self.user2.save()   
        except Exception, exc:
            print "failed user save:", str(exc)
        self.ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, str(self.user))
        models.set_default_context(self.pmap, skip_history=True)
        models.set_default_context(self.pmap, state="operational")
        utils.ensure_dir_exists(lconfig.locate_file("test.fits", self.observatory))
        utils.ensure_dir_exists(lconfig.locate_file(self.pmap, self.observatory))
        self.ingested = False
        
    def tearDown(self):
        self.remove_files(self.delete_list)
        pysh.sh("/bin/rm -rf " + lconfig.locate_file("test.fits", self.observatory), raise_on_error=True)  # , trace_commands=True)
        pysh.sh("/bin/rm -f " + sconfig.CRDS_DELIVERY_DIR + "/*")
        pysh.sh("/bin/rm -f " + sconfig.CRDS_CATALOG_DIR + "/*")
        if self.ingested:
            pysh.sh("/bin/rm -rf " + self.ingest_path, raise_on_error=True) # , trace_commands=True)
        locks.release_all()

    def login(self, username="homer", locked_instrument=None, status=302):
        instrument = locked_instrument if locked_instrument else self.locked_instrument
        response = self.client.get("/login/")
        self.assert_no_errors(response)
        response = self.client.post("/login/", {
                "username" : username,
                "password" : self.passwords[username],
                "instrument" : instrument,
            })
        self.assertEqual(response.status_code, status)
        repsponse = self.client.post("/jpoll/open_channel/")
        return response
        
    def logout(self):
        response = self.client.post("/logout/")
        self.assert_no_errors(response)
        
    def remove(self, file):
        try:
            log.verbose("Removing", repr(file))
            os.remove(file)        
        except OSError:
            pass

    def remove_files(self, files):
        for file in files:
            self.remove(file)
            self.remove(rmap.locate_file(file, self.observatory))
            self.remove(sconfig.CRDS_DELIVERY_DIR + "/" + file)

    @classmethod
    def fake_database_files(self, files, link=False):
        for filename in files:
            # log.info("Faking database file", repr(filename))
            name = os.path.basename(filename)
            source = os.path.abspath(filename)
            where = rmap.locate_file(name, self.observatory)
            if link:
                with log.error_on_exception("Symlinking", repr(source), "failed."):
                    log.info("Symlinking fake file", repr(source), "to", repr(where))
                    os.symlink(source, where)
            models.add_crds_file(
                self.observatory, name, where, 
                deliverer="homer", deliverer_email="homer@simpsons.com", 
                description="delivered by the man",
                add_slow_fields=False,
                state="archived",
                update_derivation=False)
            models.mirror_filename_counters(self.observatory, where)
            models.AuditBlob.new("homer", "mass import", name, "becuz", "some details",
                                 observatory=self.observatory)

    def install_files(self, files):
        for path in files:
            cached = rmap.locate_file(os.path.basename(path), observatory=self.observatory)
            pysh.sh("cp -f ${path} ${cached}", trace_commands=True)
            pysh.sh("chmod +r ${cached}", trace_commands=True)
            pysh.sh("chmod -wx ${cached}", trace_commands=True)

    def assert_no_errors(self, response, msg=None, status=200):
        try:            
            self.assertEqual(response.status_code, status)
            self.assertNotIn("ERROR", response.content)
            self.assertNotIn("Error", response.content)
            if msg is not None:
                self.assertIn(msg, response.content)
        except Exception, exc:
            print >>sys.stderr, str(exc)
            print >>sys.stderr, response.content
            raise
        
    def assert_has_error(self, response, msg=None, status=200):
        try:
            self.assertEqual(response.status_code, status)
            self.assertIn("ERROR", response.content)
            if msg is not None:
                self.assertIn(msg, response.content)
        except Exception, exc:
            print >>sys.stderr, str(exc)
            print >> sys.stderr, response.content
            raise

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
        if self.observatory == "hst":
            dataset1 = "interactive/test_data/j8bt05njq_raw.fits"
        else:
            dataset1 = "interactive/test_data/jw00001001001_01101_00001_MIRIMAGE_uncal.fits"
        self.fake_database_files([self.pmap])
        self.login()
        response = self.client.post("/bestrefs/", {
            "pmap_mode" : "pmap_text",
            "pmap_text" : self.pmap,
            "dataset_mode" : "dataset_uploaded",
            "dataset_uploaded" : open(dataset1),
            })  
        self.assert_no_errors(response)
    
    def add_files_to_ingest_dir(self, filepaths):
        for path in filepaths:
            self.add_file_to_ingest_dir(path)
        
    def add_file_to_ingest_dir(self, filepath):
        self.ingested = True
        ingest_file = os.path.join(self.ingest_path, os.path.basename(filepath))
        utils.ensure_dir_exists(ingest_file)
        filepath = os.path.abspath(filepath)
        try:
            log.info("testing add_files_to_ingest_dir:  linking ingest", ingest_file, "to", filepath)
            shutil.copy(filepath, ingest_file)
            os.chmod(ingest_file, 0666)
        except Exception, exc:
            log.info("failed to add file:", str(exc))
        
    def test_mark_bad_get(self):
        self.login()
        response = self.client.get("/mark_bad/")
        self.assert_no_errors(response)

    def test_mark_bad_post(self):
        self.login()
        self.fake_database_files(self.blacklist_files, link=True)
        response = self.client.post("/mark_bad/", {
            "observatory" : self.observatory,
            "file_known" : os.path.basename(self.blacklist_files[0]),
            "badflag" : "bad",
            "why" : "just had a feeling.",
            })
        rmap, imap = [ os.path.basename(file) for file in self.blacklist_files]
        self.assert_no_errors(response)
        self.assertTrue(imap in response.content)
        self.assertTrue(rmap in response.content)
        rmapblob = models.FileBlob.load(rmap)
        imapblob = models.FileBlob.load(imap)
        self.assertTrue(rmapblob.blacklisted)
        self.assertTrue(rmapblob.rejected)
        self.assertTrue(imapblob.blacklisted)
        self.assertFalse(imapblob.rejected)

    def test_certify_get(self):
        self.login()
        response = self.client.get("/certify/")
        self.assert_no_errors(response)

    def test_certify_post_fits_uploaded(self):
        self.login()
        self.fake_database_files([self.certify_post_fits])
        self.add_file_to_ingest_dir(self.certify_post_fits)
        response = self.client.post("/certify/", {
            "pmap_mode": "pmap_edit",
        })
        # print "certify post FITS response:", response.content
        self.assert_no_errors(response)
        self.assertNotIn("ERROR", response.content)
        self.assertEqual(response.content.count("OK"), 2)

    def test_certify_post_rmap_uploaded(self):
        self.login()
        self.add_file_to_ingest_dir(self.certify_rmap)
        self.fake_database_files(self.certify_rmap_fits)
        response = self.client.post("/certify/", {
            "pmap_mode": "pmap_edit",
        })
        self.assert_no_errors(response)
        self.assertTrue("ERROR", response.content)
        self.assertTrue("Failed" not in response.content)
        self.assertTrue(response.content.count("OK") == 2)

    def test_difference_get(self):
        response = self.client.get("/difference/")
        self.assert_no_errors(response)

    def test_difference_post(self):
        self.fake_database_files(self.difference_files, link=True)
        response = self.client.post("/difference/", {
            "filemode1": "file_known1",
            "file_known1" : self.difference_files[0],
            "filemode2": "file_known2",
            "file_known2" : self.difference_files[1],
        })
        self.assert_no_errors(response)
    
    def test_difference_post_uploaded(self):
        # self.fake_database_files(self.difference_files, link=True)
        self.login()
        response = self.client.post("/difference/", {
            "filemode1": "file_uploaded2",
            "file_uploaded1" : open(self.difference_files_uploaded[0]),
            "filemode2": "file_uploaded2",
            "file_uploaded2" : open(self.difference_files_uploaded[1]),
        })
        self.assert_no_errors(response)
    
    def test_recent_activity_get(self):
        response = self.client.get("/recent_activity/")
        self.assert_no_errors(response)

    def test_recent_activity_post(self):
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
        self.login()
        response = self.client.get("/create_contexts/")
        self.assert_no_errors(response)
        
    def add_1(self, name):
        """hst.pmap -->  hst_0001.pmap"""
        ext = "." + os.path.splitext(name)[-1]
        return os.path.basename(name).replace(ext, "_0001" + ext)

    def test_create_contexts_post(self):
        self.login()
        self.fake_database_files([self.pmap] + self.create_contexts_rmaps)
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
        self.fake_database_files([self.pmap])
        response = self.client.get("/browse/" + self.pmap)
        self.assert_no_errors(response)

    def test_browse_db_get(self):
        self.login()
        response = self.client.get("/browse_db/")
        self.assert_no_errors(response)

    def test_browse_db_post(self):
        self.login()
        self.fake_database_files([self.pmap])
        response = self.client.post("/browse_db/", {
                "observatory" : self.observatory,
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
        self.assertEqual(response.content.count("<tr>"), 2)

    def test_batch_submit_replace(self):
        self.login()
        self.add_files_to_ingest_dir(self.batch_submit_replace_references)
        self.fake_database_files(self.certify_rmap_fits, link=True)
        response = self.client.post("/batch_submit_references/", {
                "pmap_mode" : "pmap_edit",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "description":" this is only a test.",
                "compare_old_reference": True,
                }, follow=True)
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Cancel", response.content)
        self.assertIn("replace", response.content)
        self.assertNotIn("insert", response.content)
        self.assertIn("Reversion at", response.content)

    def _batch_submit_insert(self, references=None):
        if references is None:
            references = self.batch_submit_insert_references
        self.add_files_to_ingest_dir(references)
        self.fake_database_files(self.certify_rmap_fits)
        response = self.client.post("/batch_submit_references/", {
                "pmap_mode" : "pmap_edit",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "description":"this is only a test.",
                "auto_rename" : "checked",
            }, follow=True)
        return response
    
    def _assert_normal_bsr_insert(self, response):
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Cancel", response.content)
        self.assertIn("added", response.content)
        self.assertNotIn("replace", response.content)
    
    def _confirm(self, id=1):
        response = self.client.post("/submit_confirm/", {
                "results_id" : str(id),
                "button" : "confirm",
            }, follow=True)
        return response

    def _cancel(self, id=1):
        response = self.client.post("/submit_confirm/", {
                "results_id" : str(id),
                "button" : "cancel",
            }, follow=True)
        return response
    
    def test_batch_submit_confirm(self):
        self.login()
        response = self._batch_submit_insert()
        self._assert_normal_bsr_insert(response)
        response = self._confirm()
        self.assert_no_errors(response, msg="Submission Confirmed")
        
    def test_batch_submit_cancel(self):
        self.login()
        response = self._batch_submit_insert()
        self._assert_normal_bsr_insert(response)
        response = self._cancel()
        self.assert_no_errors(response, msg="cancelled by submitter")
    
    def test_batch_submit_broken_lock_1(self):
        self.login()
        locks.release_all()   # simulate broken locks
        response = self._batch_submit_insert()
        self.assert_has_error(response, "no longer holds lock")

    def test_batch_submit_broken_lock_2(self):
        self.login()
        response = self._batch_submit_insert()
        self._assert_normal_bsr_insert(response)
        locks.release_all()   # simulate broken locks
        response = self._confirm()
        self.assert_no_errors(response, msg="cancelled due to")

    def test_batch_submit_broken_lock_3(self):
        self.login()
        response = self._batch_submit_insert()
        self._assert_normal_bsr_insert(response)
        locks.release_all()   # simulate broken locks
        response = self._cancel()
        self.assert_no_errors(response, msg="cancelled by submitter")

    def test_login_collision(self):
        self.login()
        response = self.login("bozo", status=200)   # error page not a redirect
        self.assert_has_error(response, "has already locked")
    
    def test_submit_references_get(self):
        self.login()
        response = self.client.get("/submit/reference/")
        self.assert_no_errors(response)

    def test_submit_mapping_get(self):
        self.login()
        response = self.client.get("/submit/mapping/")
        self.assert_no_errors(response)

    def _submit_references_post(self):
        self.fake_database_files(self.submit_references)
        self.add_files_to_ingest_dir(self.submit_references)
        response = self.client.post("/submit/reference/", {
            "observatory" : self.observatory,
            "auto_rename" : "on",
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "creator" : "Somebody else",
            "pmap_mode" : "pmap_edit",
            }, follow=True)
        self.assert_no_errors(response)
        for ref in self.submit_references:
            self.assertIn(os.path.basename(ref), response.content)
        return response
    
    def test_submit_references_post_confirm(self):
        self.login()
        response = self._submit_references_post()
        response = self._confirm()
        self.assert_no_errors(response, msg="Submission Confirmed")
    
    def test_submit_references_post_cancel(self):
        self.login()
        response = self._submit_references_post()
        response = self._cancel()
        self.assert_no_errors(response, msg="cancelled by submitter")
    
    def _submit_mappings_post(self, generate_contexts):
        self.fake_database_files(self.submit_references)
        self.add_file_to_ingest_dir(self.submit_rmap)
        rmap2 = self.add_1(self.submit_rmap)
        context = {
            "observatory" : self.observatory,
            "auto_rename" : "on",
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "creator" : "Somebody else",
            "pmap_mode" : "pmap_edit",
            }
        if generate_contexts:
            context["generate_contexts"] = "on"
        response = self.client.post("/submit/mapping/", context, follow=True)
        return rmap2, response
    
    def test_submit_mappings_post_confirm(self):
        self.login()
        rmap2, response = self._submit_mappings_post(generate_contexts=False)
        self.assert_no_errors(response)
        self.assertIn(rmap2, response.content)
        response = self._confirm()
        self.assert_no_errors(response, msg="Submission Confirmed")
        
    def test_submit_mappings_post_cancel(self):
        self.login()
        rmap2, response = self._submit_mappings_post(generate_contexts=False)
        self.assert_no_errors(response)
        self.assertIn(rmap2, response.content)
        response = self._cancel()
        self.assert_no_errors(response, msg="cancelled by submitter")
        
    def test_submit_mappings_post_generate_contexts_confirm(self):
        self.login()
        rmap2, response = self._submit_mappings_post(generate_contexts=True)
        self.assert_no_errors(response)
        self.assertIn(rmap2, response.content)
        response = self._confirm()
        self.assert_no_errors(response, msg="Submission Confirmed")

    def test_submit_mappings_post_generate_contexts_cancel(self):
        self.login()
        rmap2, response = self._submit_mappings_post(generate_contexts=True)
        self.assert_no_errors(response)
        self.assertIn(rmap2, response.content)
        response = self._cancel()
        self.assert_no_errors(response, msg="cancelled by submitter")

    def test_submit_mappings_post_generate_contexts_broken_lock_1(self):
        self.login()
        locks.release_all()
        rmap2, response = self._submit_mappings_post(generate_contexts=True)
        self.assert_has_error(response, "no longer holds lock")

    def test_submit_mappings_post_generate_contexts_broken_lock_2(self):
        self.login()
        rmap2, response = self._submit_mappings_post(generate_contexts=True)
        locks.release_all()
        response = self._confirm()
        self.assertIn("cancelled due to", response.content)

    def test_submit_mappings_post_generate_contexts_broken_lock_3(self):
        self.login()
        rmap2, response = self._submit_mappings_post(generate_contexts=True)
        locks.release_all()
        response = self._cancel()
        self.assertIn("cancelled by submitter", response.content)
        
    def test_display_context_history(self):
        self.login()
        models.set_default_context(self.pmap, state="operational")
        response = self.client.get("/display_context_history/")
        self.assert_no_errors(response)
    
    def test_set_context_get(self):
        self.login()
        response = self.client.get("/set_default_context/")
        self.assert_no_errors(response)
    
    def test_set_context_post(self):
        self.login()
        self.install_files([self.new_context])
        self.fake_database_files([self.new_context])
        new_context = os.path.basename(self.new_context)
        response = self.client.post("/set_default_context/", {
            "context_type" : "operational",
            "pmap_mode" : "pmap_text",
            "pmap_text" : new_context,
            "description" : "a reason for the new context.",
        })
        # print "certify post FITS response:", response.content
        self.assert_no_errors(response)
        self.assertNotIn("ERROR", response.content)
        self.assertEqual(
            models.get_default_context(observatory=self.observatory, state="operational"), 
            new_context)
        first_history = models.get_context_history(
            observatory=self.observatory, state="operational")[0].context
        self.assertEqual(new_context, first_history)
        #  XXX check history
    
    def test_get(self):   # XXX TODO implememnt get test
        pass

if sconfig.observatory == "hst":
    
    class Hst(InteractiveBase, TransactionTestCase):

        def __init__(self, *args, **keys):
            super(Hst, self).__init__(*args, **keys)
        
        observatory = "hst"
        pmap = "hst.pmap"
        
        new_context = "interactive/test_data/hst_0027.pmap"
        
        delete_list = [
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
            "hst_cos_deadtab_0001.fits",
            "hst_cos_deadtab_0002.fits",
            "opus_1_i.cat",
        ]

        rmap1 = "interactive/test_data/hst_cos_deadtab.rmap"

        difference_files = ["hst_acs.imap", "hst_cos.imap"]
        difference_files_uploaded = ["interactive/test_data/hst_acs.imap", 
                                     "interactive/test_data/hst_cos.imap"]

        certify_rmap = "interactive/test_data/hst_cos_deadtab.rmap"
        certify_rmap_fits = ["s7g1700ql_dead.fits", "interactive/test_data/s7g1700gl_dead.fits", 
                             "t9e1307kl_disp.fits", "u1t1616pl_disp.fits",
                             "s7g17013l_disp.fits", "v3g18194l_disp.fits",
                             "x6q17584l_disp.fits", "x1v17415l_disp.fits",
                             "s7g17013l_disp.fits", "t9e1307ll_disp.fits",
                             "u6s1320ql_disp.fits", "interactive/test_data/t2k1224el_disp.fits"]

        certify_post_fits = "interactive/test_data/s7g1700gl_dead.fits"
        
        submit_rmap = "interactive/test_data/hst_cos_deadtab_9999.rmap"
        submit_references = [
                "interactive/test_data/s7g1700gl_dead.fits", 
                "interactive/test_data/s7g1700ql_dead.fits"
        ]
        locked_instrument = "cos"         

        batch_submit_replace_references = ["interactive/test_data/s7g1700gj_dead.fits",
                                           "interactive/test_data/aaaa.fits"]
#        batch_submit_comparison_references = ["interactive/test_data/s7g1700gl_dead.fits",
#                                              "interactive/test_data/t2k1224el_disp.fits"]
        batch_submit_insert_references = ["interactive/test_data/s7g1700gm_dead.fits"]
        
        create_contexts_rmaps = ["hst_acs_biasfile.rmap", "hst_cos_deadtab.rmap"]

        blacklist_files = [  # order critical, dependencies must be added first.
            "interactive/test_data/hst_acs_darkfile2.rmap",
            "interactive/test_data/hst_acs2.imap",
            ]
else:  # JWST
    
    class Jwst(InteractiveBase, TransactionTestCase):

        def __init__(self, *args, **keys):
            super(Jwst, self).__init__(*args, **keys)

        observatory = "jwst"
        pmap = "jwst_0000.pmap"
        
        new_context = "interactive/test_data/jwst_0027.pmap"
        
        delete_list = [
            "jwst_0001.pmap",
            "jwst_0002.pmap",
            "jwst_miri_0001.imap",
            "jwst_miri_0002.imap",
            "jwst_nircam_0001.imap",
            "jwst_miri_flat_0001.rmap",
            "jwst_miri_amplifier_0002.rmap",
            "jwst_miri_photom_0002.rmap",
            "jwst_miri_amplifier_0001.fits",
            "jwst_miri_amplifier_0002.fits",
            "jwst_miri_amplifier_0003.fits",
            "jwst_miri_amplifier_0004.fits",
            "jwst_miri_amplifier_0005.fits",
            "jwst_miri_amplifier_0006.fits",
            "jwst_miri_photom_0001.rmap",
            "jwst_miri_amplifier_9999.rmap",
            "jwst_miri_amplifier_9998.fits",
            "opus_1_i.cat",
        ]

        difference_files = ["jwst_miri_0000.imap", 
                            "jwst_nircam_0000.imap"]

        difference_files_uploaded = ["interactive/test_data/jwst_miri_0000.imap", 
                                     "interactive/test_data/jwst_nircam_0000.imap"]

        certify_rmap = "interactive/test_data/jwst_miri_amplifier_0000.rmap"
        certify_rmap_fits = ["jwst_miri_amplifier_0000.fits",
                             "jwst_miri_amplifier_0001.fits",
                             "jwst_miri_amplifier_0002.fits"]
        certify_post_fits = "interactive/test_data/jwst_miri_amplifier_0001.fits"

        submit_rmap = "interactive/test_data/jwst_miri_amplifier_9999.rmap"
        submit_references = ["interactive/test_data/jwst_miri_amplifier_0000.fits",
                             "interactive/test_data/jwst_miri_amplifier_0001.fits"]        
        locked_instrument = "miri"

        batch_submit_replace_references = ["interactive/test_data/jwst_miri_amplifier_0000.fits",
                                           "interactive/test_data/jwst_miri_photom_9999.fits"]
        batch_submit_insert_references = ["interactive/test_data/jwst_miri_amplifier_9998.fits",
                                          "interactive/test_data/jwst_miri_photom_9998.fits"]
        
        create_contexts_rmaps = ["jwst_miri_amplifier_0000.rmap", 
                                 "jwst_miri_photom_0000.rmap"]

        blacklist_files = [
            "interactive/test_data/jwst_miri_0000.imap",
            "interactive/test_data/jwst_miri_amplifier_9999.rmap",
            ]

