"""Unit tests to exercise the interactive portions of the CRDS server."""
import sys
import os
import shutil
import os.path

from django.test import TransactionTestCase, TestCase

from crds.core import (rmap, utils, pysh, log)
from crds.core import config as lconfig

from .. import settings
from .. import config as sconfig
from . import models, locks, mail, views, confirm

from django.contrib.auth.models import User

# pysh.set_debug(True) # XXXXX set False for production unit test use, True for development.

class DecodedResponse(object):

    def __init__(self, response):
        self.response = response

    def __getattr__(self, attr):
        if attr == "content":
            return self.response.content.decode("utf-8")
        else:
            return getattr(self.response, attr)

class InteractiveBase(TransactionTestCase):

    __test__ = False

    @classmethod
    def setUpClass(cls):
        
        print()
        print("="*80)
        print()

        log.info("Setting up tests:", cls.__name__)

        super(InteractiveBase, cls).setUpClass()

        global REAL_CRDS_PATH, CRDS_PATH, TEST_MAPPING_DIR, REAL_MAPPING_DIR

        # The results of locate_file will change when CRDS_PATH is redefined below.
        # Remember the real one here.
        REAL_MAPPING_DIR = os.path.dirname(rmap.locate_file("foo.pmap", cls.observatory))

        # Must cache before CRDS_PATH changes to test cache.
        cls._cached_mapping_names = []
        for mapping in cls.cached_contexts:
            cls._cached_mapping_names.extend(rmap.load_mapping(mapping).mapping_names())
        cls._cached_mapping_names = sorted(set(cls._cached_mapping_names))
        
        REAL_CRDS_PATH = os.environ["CRDS_PATH"]
        CRDS_PATH = os.environ["CRDS_PATH"] = sconfig.install_root + "/test"
        TEST_MAPPING_DIR = os.path.dirname(lconfig.locate_file("test.pmap", cls.observatory))

        # Set up test server tree and CRDS test cache
        lconfig.set_crds_ref_subdir_mode("flat", cls.observatory)

        log.info("Test CRDS_PATH", CRDS_PATH, "environ", os.environ["CRDS_PATH"], 
                 "REAL_MAPPING_DIR", REAL_MAPPING_DIR, "TEST_MAPPING_DIR", TEST_MAPPING_DIR)


        pysh.sh("rm -rf ${CRDS_PATH}", raise_on_error=True)  #, trace_commands=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/ingest", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/deliveries", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/catalogs", raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/references/%s" % cls.observatory, raise_on_error=True)
        pysh.sh("mkdir -p ${CRDS_PATH}/mappings/%s" % cls.observatory, raise_on_error=True)

        # monkey-patch these since they're not encapsulated with functions.
        sconfig.CRDS_INGEST_DIR = os.path.join(CRDS_PATH, "ingest")
        sconfig.CRDS_DELIVERY_DIR = os.path.join(CRDS_PATH, "deliveries")
        sconfig.CRDS_DELIVERY_DIRS = [os.path.join(CRDS_PATH, "deliveries")]
        sconfig.CRDS_CATALOG_DIR = os.path.join(CRDS_PATH, "catalogs")
        sconfig.FILE_UPLOAD_TEMP_DIR = os.path.join(CRDS_PATH, "uploads")
        settings.CRDS_LOCK_ACQUIRE_TIMEOUT = 0.5  # Don't waste time during tests with SQLite

        def null_func(*args, **keys):
            pass
        mail.mail = null_func

    @classmethod
    def tearDownClass(cls):
        super(InteractiveBase, cls).tearDownClass()
        CRDS_PATH = os.environ["CRDS_PATH"] = sconfig.install_root + "/test"
        print()
        print("="*80)
        print()

    @classmethod
    def copy_test_mappings(cls):
        CRDS_PATH = os.environ["CRDS_PATH"] = sconfig.install_root + "/test"
        mappings = "{" + ",".join(cls._cached_mapping_names) + "}"
        pysh.sh("cp -f ${REAL_MAPPING_DIR}/${mappings} ${CRDS_PATH}/mappings/%s" % cls.observatory, 
                raise_on_error=True) # , trace_commands=True)
        pysh.sh("cp -rf ${REAL_CRDS_PATH}/config ${CRDS_PATH}/config",
                raise_on_error=True) # , trace_commands=True)
        for mapping in cls.mapping_overrides:
            mapping = os.path.abspath(os.path.join(os.getcwd(), mapping))
            pysh.sh("cp -f %s ${CRDS_PATH}/mappings/%s" % (mapping, cls.observatory),
                    raise_on_error=True) # , trace_commands=True)

    passwords = {
        "homer" : "simposon",
        "bozo" : "the clown",
    }
    
    def setUp(self): 
        super(InteractiveBase, self).setUp()
        self.copy_test_mappings()
        self.user = User.objects.create_user('homer', 'homer@simpson.net', self.passwords["homer"])
        self.user2 = User.objects.create_user('bozo', 'bozo@godaddy.com', self.passwords["bozo"])
        self.user.is_superuser = True
        try:
            self.user.save() 
            self.user2.save()   
        except Exception as exc:
            print("failed user save:", str(exc))
        self.ingest_path = os.path.join(sconfig.CRDS_INGEST_DIR, str(self.user))
        self.fake_database_files(list(set([self.pmap, self.pmap2, self.pmap3])))
        models.set_default_context(self.pmap, skip_history=True)
        models.set_default_context(self.pmap, state="operational")
        utils.ensure_dir_exists(os.path.join(lconfig.get_crds_refpath(self.observatory), "test.fits"))
        utils.ensure_dir_exists(os.path.join(lconfig.get_crds_mappath(self.observatory), "test.pmap"))
        self.ingested = False
        
    def tearDown(self):
        super(InteractiveBase, self).tearDown()
        self.remove_files(self.delete_list)
        # pysh.sh("/bin/rm -rf " + lconfig.locate_file("test.fits", self.observatory), raise_on_error=True)  # , trace_commands=True)
        pysh.sh("/bin/rm -f " + sconfig.CRDS_DELIVERY_DIR + "/*")
        pysh.sh("/bin/rm -f " + sconfig.CRDS_CATALOG_DIR + "/*")
        if self.ingested:
            pysh.sh("/bin/rm -rf " + self.ingest_path, raise_on_error=True) # , trace_commands=True)
        locks.release_all()
        print("-"*80)
        print()
            
    def get(self, *args, **keys):
        raw_response = self.client.get(*args, **keys)
        return DecodedResponse(raw_response)

    def post(self, *args, **keys):
        raw_response = self.client.post(*args, **keys)
        response = DecodedResponse(raw_response)
        # log.info("RESPONSE:\n", response.content)
        return response

    def login(self, username="homer", locked_instrument=None, status=302):
        instrument = locked_instrument if locked_instrument else self.locked_instrument
        response = self.get("/login/")
        self.assert_no_errors(response)
        response = self.post("/login/", {
                "username" : username,
                "password" : self.passwords[username],
                "instrument" : instrument,
            })
        self.assertEqual(response.status_code, status)
        repsponse = self.post("/jpoll/open_channel/")
        return response
        
    def logout(self):
        response = self.post("/logout/")
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
            if not file.endswith(".cat"):
                self.remove(rmap.locate_file(file, self.observatory))
            self.remove(sconfig.CRDS_DELIVERY_DIR + "/" + file)

    @classmethod
    def fake_database_files(self, files, link=False):
        for filename in files:
            log.info("Faking database file", repr(filename))
            name = os.path.basename(filename)
            if not os.path.dirname(filename):
                source = os.path.abspath(os.getcwd() + "/interactive/test_data/" + filename)
            else:
                source = os.path.abspath(filename)
            where = lconfig.relocate_file(filename, self.observatory)
            if link and not os.path.exists(where):
                with log.error_on_exception("Symlinking", repr(source), "to", repr(where), "failed."):
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
            pysh.sh("cp -f ${path} ${cached}") # , trace_commands=True)
            pysh.sh("chmod +r ${cached}") # , trace_commands=True)
            pysh.sh("chmod -wx ${cached}") # , trace_commands=True)

    def assert_no_errors(self, response, msg=None, status=200):
        try:            
            self.assertEqual(response.status_code, status)
            self.assertNotIn("ERROR", response.content)
            # self.assertNotIn("Error", response.content)
            if msg is not None:
                self.assertIn(msg, response.content)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            print(response.content, file=sys.stderr)
            raise
        
    def assert_has_error(self, response, msg=None, status=200):
        try:
            self.assertEqual(response.status_code, status)
            self.assertIn("ERROR", response.content)
            if msg is not None:
                self.assertIn(msg, response.content)
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            print(response.content, file=sys.stderr)
            raise

    def test_index(self):
        response = self.get('/')
        self.assert_no_errors(response)

    def test_logout(self):
        response = self.get("/logout/") 
        self.assert_no_errors(response, status=302) #redirect
    
    def test_bestrefs(self):
        response = self.get("/bestrefs/")
        self.assert_no_errors(response)

    def _set_pmap2_defaults(self):
        models.set_default_context(self.pmap2, skip_history=True)
        models.set_default_context(self.pmap2, state="operational")

    # XXX Implement bestrefs tests
    def test_bestrefs_post_archive_dataset(self):
        self._set_pmap2_defaults()
        response = self.post("/bestrefs/", {
            "pmap_mode" : "pmap_text",
            "pmap_text" : self.pmap2,
            "dataset_mode" : "dataset_archive",
            "dataset_archive" : self.archive_dataset_id,
            })  
        self.assert_no_errors(response)
    
    def test_bestrefs_post_default_context(self):
        self._set_pmap2_defaults()
        response = self.post("/bestrefs/", {
            "pmap_mode" : "pmap_edit",
            "pmap_edit" : self.pmap2,
            "dataset_mode" : "dataset_archive",
            "dataset_archive" : self.archive_dataset_id, 
            })  
        self.assert_no_errors(response)
    
    def test_bestrefs_post_uploaded_dataset(self):
        if self.observatory == "hst":
            dataset1 = "interactive/test_data/j8bt05njq_raw.fits"
        else:
            dataset1 = "interactive/test_data/jw00001001001_01101_00001_MIRIMAGE_uncal.fits"
        self.login()
        self._set_pmap2_defaults()
        response = self.post("/bestrefs/", {
            "pmap_mode" : "pmap_text",
            "pmap_text" : self.pmap3,
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
            os.chmod(ingest_file, 0o666)
        except Exception as exc:
            log.info("failed to add file:", str(exc))
        
    def test_mark_bad_get(self):
        self.login()
        response = self.get("/mark_bad/")
        self.assert_no_errors(response)

    def test_mark_bad_post(self):
        self.login()
        self.fake_database_files(self.blacklist_files, link=True)
        response = self.post("/mark_bad/", {
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
        response = self.get("/certify/")
        self.assert_no_errors(response)

    def test_certify_post_rmap_uploaded(self):
        self.login()
        self.add_file_to_ingest_dir(self.certify_rmap)
        self.fake_database_files(self.certify_rmap_fits)
        response = self.post("/certify/", {
            "pmap_mode": "pmap_edit",
        }, follow=True)
        self.assert_no_errors(response)
        self.assertNotIn("ERROR", response.content)
        self.assertNotIn("Failed", response.content)
        self.assertEqual(response.content.count("OK"), 2)

    def test_difference_get(self):
        response = self.get("/difference/")
        self.assert_no_errors(response)

    def test_difference_post(self):
        self.fake_database_files(self.difference_files, link=True)
        response = self.post("/difference/", {
            "filemode1": "file_known1",
            "file_known1" : self.difference_files[0],
            "filemode2": "file_known2",
            "file_known2" : self.difference_files[1],
        })
        self.assert_no_errors(response)
    
    def test_difference_post_uploaded(self):
        # self.fake_database_files(self.difference_files, link=True)
        self.login()
        response = self.post("/difference/", {
            "filemode1": "file_uploaded2",
            "file_uploaded1" : open(self.difference_files_uploaded[0]),
            "filemode2": "file_uploaded2",
            "file_uploaded2" : open(self.difference_files_uploaded[1]),
        })
        self.assert_no_errors(response)
    
    def test_recent_activity_get(self):
        response = self.get("/recent_activity_input/")
        self.assert_no_errors(response)

    def test_recent_activity_post(self):
        response = self.post("/recent_activity_query/", {
                "action" : "new context",
                "observatory" : "*",
                "instrument" : "*",
                "filekind" : "*",
                "extension" : "*",
                "filename" : "*",
                "deliverer_user" : "*",
                "start_date": "*",
                "stop_date": "*",
            })
        self.assert_no_errors(response)

    def test_create_contexts(self):
        self.login()
        response = self.get("/create_contexts/")
        self.assert_no_errors(response)
        
    def add_1(self, name):
        """hst.pmap -->  hst_0001.pmap"""
        ext = "." + os.path.splitext(name)[-1]
        return os.path.basename(name).replace(ext, "_0001" + ext)

    def test_create_contexts_post(self):
        self.login()
        self.fake_database_files(self.create_contexts_rmaps)
        response = self.post("/create_contexts/", {
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
        response = self.get("/browse/" + self.pmap)
        self.assert_no_errors(response)

    def test_browse_db_get(self):
        self.login()
        response = self.get("/browse_db/")
        self.assert_no_errors(response)

    def test_browse_db_post(self):
        self.login()
        response = self.post("/browse_db/", {
                "observatory" : self.observatory,
                "instrument" : "*",
                "filekind" : "*",
                "extension": "*",
                "filename": self.pmap,
                "deliverer_user": "*",
                "status":"*",
                "start_date": "*",
                "stop_date": "*",
            })
        # print response
        self.assert_no_errors(response)
        self.assertTrue(self.pmap in response.content)
        self.assertEqual(response.content.count("<tr>"), 2)

    def test_batch_submit_replace(self):
        self.login()
        self.add_files_to_ingest_dir(self.batch_submit_replace_references)
        self.fake_database_files(self.certify_rmap_fits, link=True)
        response = self.post("/batch_submit_references/", {
                "pmap_mode" : "pmap_edit",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "description":" this is only a test.",
                "compare_old_reference": True,
                "auto_rename" : "checked",
                }, follow=True)
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Cancel", response.content)
        self.assertIn("replace", response.content)
        self.assertNotIn("insert", response.content)
        # self.assertIn("Reversion at", response.content)

    def _batch_submit_insert(self, references=None):
        if references is None:
            references = self.batch_submit_insert_references
        self.add_files_to_ingest_dir(references)
        self.fake_database_files(references, link=True)
        response = self.post("/batch_submit_references/", {
                "pmap_mode" : "pmap_edit",
                "creator" : "bozo",
                "change_level" : "SEVERE",
                "description":"this is only a test.",
                "auto_rename" : "checked",
            }, follow=True)
        return response

    def test_batch_submit_truncated(self):
        self.login()
        response = self._batch_submit_insert(self.batch_submit_truncated_references)
        # doesn't guarantee same message but any WARNING will trigger top level notice
        self.assertTrue(("probable file truncation" in response.content) or
                        ("*** Error:   checking data fill" in response.content))

    def _assert_normal_bsr_insert(self, response):
        # print response
        self.assert_no_errors(response)
        self.assertIn("Confirm or Cancel", response.content)
        self.assertIn("added", response.content)
        self.assertNotIn("replace", response.content)
    
    def _confirm(self, id=1):
        blob = models.RepeatableResultBlob.get(id)
        response = self.post("/submit_confirm/", {
                "results_id" : str(blob.name),
                "button" : "confirm",
            }, follow=True)
        return response

    def _cancel(self, id=1):
        blob = models.RepeatableResultBlob.get(id)
        response = self.post("/submit_confirm/", {
                "results_id" : str(blob.name),
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
        self.assert_no_errors(response, msg="canceled")
    
    # def test_batch_submit_broken_lock_1(self):
    #     self.login()
    #     locks.release_all()   # simulate broken locks
    #     response = self._batch_submit_insert()
    #     self.assert_has_error(response, "no longer holds lock")

    # def test_batch_submit_broken_lock_2(self):
    #     self.login()
    #     response = self._batch_submit_insert()
    #     self._assert_normal_bsr_insert(response)
    #     locks.release_all()   # simulate broken locks
    #     response = self._confirm()
    #     self.assert_no_errors(response, msg="canceled due to")

    # def test_batch_submit_broken_lock_3(self):
    #     self.login()
    #     response = self._batch_submit_insert()
    #     self._assert_normal_bsr_insert(response)
    #     locks.release_all()   # simulate broken locks
    #     response = self._cancel()
    #     self.assert_no_errors(response, msg="canceled by submitter")

    def test_login_collision(self):
        self.login()
        response = self.login("bozo", status=200)   # error page not a redirect
        self.assert_has_error(response, "has already locked")
    
    def test_submit_references_get(self):
        self.login()
        response = self.get("/submit/reference/")
        self.assert_no_errors(response)

    def test_submit_mapping_get(self):
        self.login()
        response = self.get("/submit/mapping/")
        self.assert_no_errors(response)

    def _submit_references_post(self):
        self.fake_database_files(self.submit_references, link=True)
        self.add_files_to_ingest_dir(self.submit_references)
        response = self.post("/submit/reference/", {
            "observatory" : self.observatory,
            "auto_rename" : "on",
            "description" : "an identical pmap with a different name is still different",
            "change_level" : "SEVERE",
            "creator" : "Somebody else",
            "pmap_mode" : "pmap_edit",
            "generate_contexts" : False,
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
        self.assert_no_errors(response, msg="canceled")
    
    def _submit_mappings_post(self, generate_contexts):
        self.fake_database_files(self.submit_references, link=True)
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
        response = self.post("/submit/mapping/", context, follow=True)
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
        self.assert_no_errors(response, msg="canceled")
        
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
        self.assert_no_errors(response, msg="canceled")

    # def test_submit_mappings_post_generate_contexts_broken_lock_1(self):
    #     self.login()
    #     locks.release_all()
    #     rmap2, response = self._submit_mappings_post(generate_contexts=True)
    #     self.assert_has_error(response, "no longer holds lock")

    # def test_submit_mappings_post_generate_contexts_broken_lock_2(self):
    #     self.login()
    #     rmap2, response = self._submit_mappings_post(generate_contexts=True)
    #     locks.release_all()
    #     response = self._confirm()
    #     self.assertIn("canceled due to", response.content)

    # def test_submit_mappings_post_generate_contexts_broken_lock_3(self):
    #     self.login()
    #     rmap2, response = self._submit_mappings_post(generate_contexts=True)
    #     locks.release_all()
    #     response = self._cancel()
    #     self.assertIn("canceled by submitter", response.content)
        
    def test_display_context_history(self):
        self.login()
        models.set_default_context(self.pmap, state="operational")
        response = self.get("/display_context_history/")
        self.assert_no_errors(response)
    
    def test_context_table(self):
        models.set_default_context(self.pmap, state="operational")
        response = self.get("/context_table/" + self.pmap)
        self.assert_no_errors(response)

    def test_set_context_get(self):
        self.login()
        response = self.get("/set_default_context/")
        self.assert_no_errors(response)
    
    def test_set_context_post(self):
        self.login()
        self.install_files([self.new_context])
        self.fake_database_files([self.new_context], link=True)
        new_context = os.path.basename(self.new_context)
        response = self.post("/set_default_context/", {
            "context_type" : "operational",
            "pmap_mode" : "pmap_text",
            "pmap_text" : new_context,
            "description" : "a reason for the new context.",
        })
        # print "certify post FITS response:", response.content
        self.assert_no_errors(response)
        self.assertNotIn("ERROR", response.content)
        self.assertEqual(
            models.get_default_context(self.observatory, "operational"), 
            new_context)
        first_history = models.get_context_history(
            observatory=self.observatory, state="operational")[0].context
        self.assertEqual(new_context, first_history)
        #  XXX check history
    
    def test_get(self):   # XXX TODO implememnt get test
        pass

    def test_upload_link(self):
        """This checks to ensure upload_path and ingest_path are on the same
        file system and are amenable to hard-linking.  File system automounts
        can make this fail.
        """
        upload_path = os.path.join(sconfig.FILE_UPLOAD_TEMP_DIR, "test.upload")
        self._core_link_test(upload_path)

    def test_upload_link_intentional_fail(self):
        """This checks the upload link test strategy for viability by intentionally
        cross-linking upload and ingest directories.  If it fails it is
        not inherently a problem as long as test_upload_link() also succeeds.
        """
        upload_path = "/tmp/test.upload"
        with self.assertRaises(OSError) as e:
            self._core_link_test(upload_path)

    def _core_link_test(self, upload_path):
        utils.ensure_dir_exists(upload_path)
        with open(upload_path, "w+") as temp:
            temp.write("no-cross-links upload test file.\n")
        ingest_path = confirm.get_ingest_path("homer", "test.upload")
        views.link_upload_to_ingest(upload_path, ingest_path)
        os.remove(upload_path)
        os.remove(ingest_path)

# ----------------------------------------------------------------------------------

if sconfig.observatory == "hst":
    
    class Hst(InteractiveBase):

        observatory = "hst"
        pmap = pmap2 = pmap3 = "hst.pmap"
        cached_contexts = [pmap]
        
        new_context = "interactive/test_data/hst_0027.pmap"

        mapping_overrides = [
            ]
        
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
        certify_rmap_bad = "interactive/test_data/hst_cos_deadtab_bad.rmap"
        certify_rmap_fits = ["s7g1700ql_dead.fits", "interactive/test_data/s7g1700gl_dead.fits", 
                             "t9e1307kl_disp.fits", "u1t1616pl_disp.fits",
                             "s7g17013l_disp.fits", "v3g18194l_disp.fits",
                             "x6q17584l_disp.fits", "x1v17415l_disp.fits",
                             "s7g17013l_disp.fits", "t9e1307ll_disp.fits",
                             "u6s1320ql_disp.fits", "interactive/test_data/t2k1224el_disp.fits"]

        certify_post_fits = "interactive/test_data/s7g1700gl_dead.fits"
        certify_post_fits_bad = "interactive/test_data/s7g1700rl_dead_bad.fits"
        
        submit_rmap = "interactive/test_data/hst_cos_deadtab_9999.rmap"
        submit_references = [
                "interactive/test_data/s7g1700gl_dead.fits", 
                "interactive/test_data/s7g1700ql_dead.fits"
        ]
        locked_instrument = "cos"         

        batch_submit_replace_references = ["interactive/test_data/s7g1700hl_dead.fits",
                                           "interactive/test_data/a7g1700al_dead.fits"]

#        batch_submit_comparison_references = ["interactive/test_data/s7g1700gl_dead.fits",
#                                              "interactive/test_data/t2k1224el_disp.fits"]
        batch_submit_insert_references = ["interactive/test_data/s7g1700hl_dead.fits"]
        
        batch_submit_truncated_references = ["interactive/test_data/hst_truncated.fits"] 

        create_contexts_rmaps = ["hst_acs_biasfile.rmap", "hst_cos_deadtab.rmap"]

        blacklist_files = [  # order critical, dependencies must be added first.
            "interactive/test_data/hst_acs_darkfile2.rmap",
            "interactive/test_data/hst_acs2.imap",
            ]

        archive_dataset_id = "I9ZF01010"

        def test_certify_post_rmap_bad(self):
            self.login()
            self.add_file_to_ingest_dir(self.certify_rmap_bad)
            self.fake_database_files(self.certify_rmap_fits)
            response = self.post("/certify/", {
                    "pmap_mode": "pmap_edit",
                    "compare_old_reference": "checked",
                    }, follow=True)
            self.assertTrue(response.content.count("ERROR") == 5)
            self.assertTrue(response.content.count("WARNING") == 3)
            self.assertIn("sha1sum", response.content)
            self.assertIn("is not in", response.content)
            self.assertIn("Reversion", response.content)
            self.assertIn("Duplicate", response.content)
            self.assertTrue(response.content.count("is not known") == 2)
            
        def test_certify_post_fits_bad(self):
            self.login()
            self.fake_database_files([self.certify_post_fits_bad])
            self.add_file_to_ingest_dir(self.certify_post_fits_bad)
            response = self.post("/certify/", {
                    "pmap_mode": "pmap_edit",
                    }, follow=True)
            # print "certify post FITS response:", response.content
            self.assertIn("&#39;FOO&#39; is not one of", response.content)
            self.assertIn("ERROR", response.content)
            self.assertIn("s7g1700rl_dead_bad.fits  <span class=\'red\'>Failed.</span>", response.content)
            
        def test_certify_post_fits_uploaded(self):
            self.login()
            self.fake_database_files([self.certify_post_fits])
            self.add_file_to_ingest_dir(self.certify_post_fits)
            response = self.post("/certify/", {
                    "pmap_mode": "pmap_edit",
                    }, follow=True)
            # print "certify post FITS response:", response.content
            self.assert_no_errors(response)
            self.assertNotIn("ERROR", response.content)
            self.assertEqual(response.content.count("OK"), 2)
            
else:  # JWST
    
    class Jwst(InteractiveBase):

        observatory = "jwst"
        pmap = "jwst_0000.pmap"
        pmap2 = "jwst_0082.pmap"
        pmap3 = "jwst_0341.pmap"

        cached_contexts = [pmap, "jwst_0003.pmap", pmap2, pmap3]

        new_context = "interactive/test_data/jwst_0027.pmap"
        
        mapping_overrides = [
            "interactive/test_data/jwst_miri_amplifier_0000.rmap",
            "interactive/test_data/jwst_miri_amplifier_9999.rmap",
            "interactive/test_data/jwst_miri_photom_0000.rmap",
            "interactive/test_data/jwst_miri_photom_0666.rmap",
            "interactive/test_data/jwst_miri_photom_9999.rmap",
            ]

        delete_list = [
            "jwst_0001.pmap",
            "jwst_0002.pmap",
            "jwst_0083.pmap",
            "jwst_0084.pmap",
            "jwst_0342.pmap",
            "jwst_0343.pmap",
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
        certify_rmap_bad = "interactive/test_data/jwst_miri_photom_0666.rmap"
        certify_rmap_fits = ["interactive/test_data/jwst_miri_amplifier_0000.fits",
                             "interactive/test_data/jwst_miri_amplifier_0001.fits",
                             "interactive/test_data/jwst_miri_amplifier_0002.fits",
                             "interactive/test_data/jwst_miri_photom_0000.fits",
                             "interactive/test_data/jwst_miri_photom_8888.fits",
                             "interactive/test_data/jwst_miri_photom_8889.fits",
                             "interactive/test_data/jwst_0003.pmap",
                             ]
        certify_post_fits = "interactive/test_data/jwst_miri_amplifier_0001.fits"

        submit_rmap = "interactive/test_data/jwst_miri_amplifier_9999.rmap"
        submit_references = ["interactive/test_data/jwst_miri_amplifier_0000.fits",
                             "interactive/test_data/jwst_miri_amplifier_0001.fits",
                             "interactive/test_data/jwst_miri_amplifier_0002.fits",
                             ]        
        locked_instrument = "miri"

        batch_submit_replace_references = ["interactive/test_data/jwst_miri_amplifier_0000.fits",
                                           "interactive/test_data/jwst_miri_photom_9999.fits"]
        batch_submit_insert_references = ["interactive/test_data/jwst_miri_amplifier_9998.fits",
                                          "interactive/test_data/jwst_miri_photom_9998.fits"]

        batch_submit_truncated_references = ["interactive/test_data/jwst_truncated.fits"]
        
        create_contexts_rmaps = ["jwst_miri_amplifier_0000.rmap", 
                                 "jwst_miri_photom_0000.rmap"]

        blacklist_files = [
            "interactive/test_data/jwst_miri_amplifier_9999.rmap",
            "interactive/test_data/jwst_miri_6666.imap",
            ]
        
        archive_dataset_id = "JW93135336001_02102_00001.MIRIFUSHORT"

        certify_post_fits_bad = "interactive/test_data/jwst_miri_amplifier_bad.fits"

        def test_certify_post_rmap_bad(self):
            self.login()
            self.add_file_to_ingest_dir(self.certify_rmap_bad)
            self.fake_database_files(self.certify_rmap_fits)
            response = self.post("/certify/", {
                    "pmap_mode": "pmap_text",
                    "pmap_text": "jwst_0003.pmap",
                    "compare_old_reference": "checked",
                    }, follow=True)
            self.assertTrue(response.content.count("ERROR") == 3)
            self.assertTrue(response.content.count("WARNING") == 3)
            self.assertIn("sha1sum", response.content)
            self.assertIn("is not in", response.content)
            self.assertIn("Reversion", response.content)
            self.assertIn("Duplicate", response.content)
            self.assertIn("is not known", response.content)
            
        def test_certify_post_fits_bad(self):
            self.login()
            self.fake_database_files([self.certify_post_fits_bad])
            self.add_file_to_ingest_dir(self.certify_post_fits_bad)
            response = self.post("/certify/", {
                    "pmap_mode": "pmap_edit",
                    }, follow=True)
            # print "certify post FITS response:", response.content
            # self.assertIn("&#39;FOO&#39; is not one of", response.content)
            # self.assertIn("ERROR", response.content)
            # self.assertIn("s7g1700rl_dead_bad.fits  <span class=\'red\'>Failed.</span>", response.content)
            
        def test_certify_post_fits_uploaded(self):
            self.login()
            self.fake_database_files([self.certify_post_fits])
            self.add_file_to_ingest_dir(self.certify_post_fits)
            response = self.post("/certify/", {
                    "pmap_mode": "pmap_edit",
                    }, follow=True)
            print("certify post FITS response:", response.content)
            self.assert_no_errors(response)
            self.assertNotIn("ERROR", response.content)
            self.assertEqual(response.content.count("OK"), 1)
            self.assertEqual(response.content.count("Warnings"), 2)

