"""These tests exercise the functions in the CRDS client API.
"""
import sys
import os
import os.path
import re

# from django.test import TestCase
from unittest import TestCase

import crds
import crds.config

from crds import pysh, rmap, selectors, log, pysh, heavy_client, timestamp
import crds.client as client
import crds.server.config as server_config
from crds.server.interactive import models as imodels
from crds.server.jsonapi import views

class ServiceApiBase(object):

    @classmethod
    def setUpClass(self, *args, **keys):
        
        self.CRDS_PATH = CRDS_PATH = os.environ["CRDS_PATH"] = server_config.storage_path + "/test"

        pysh.sh("rm -rf ${CRDS_PATH}", raise_on_error=True, trace_commands=True)
        pysh.sh("mkdir -p ${CRDS_PATH}", raise_on_error=True)
        os.environ.pop("CRDS_MAPPATH", None)
        os.environ.pop("CRDS_REFPATH", None)
        client.set_crds_server(server_config.CRDS_URL)
    
    @classmethod
    def tearDownClass(self, *args, **keys):
        os.environ["CRDS_PATH"] = server_config.install_root

    def get_header(self):
        return dict(self.header)
    
    def expected_references(self):
        raise NotImplementedError("ServiceApiTest is abstract: subclass and define expected_references().")

    def get_bestrefs(self, reftypes=[]):
        header = self.get_header()
        return client.get_best_references(self.pmap, header, reftypes)

    def purge_mappings(self):
        pysh.sh("rm -rf " + self.CRDS_PATH)        
        
    def purge_references(self):
        pysh.sh("rm -rf " + self.CRDS_PATH)

    def test_client_dump_mappings(self):
        client.dump_mappings(self.pmap)
        self.purge_mappings()

    def _check_bestrefs(self, bestrefs, reftypes):    
        for key in reftypes:
            value = self.expected_references()[key]
            self.assertIn(key, bestrefs)
            self.assertEqual(os.path.basename(bestrefs[key]), value)

    def test_client_get_bestrefs_all(self):
        bestrefs = self.get_bestrefs()
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_client_get_bestrefs_some(self):
        bestrefs = self.get_bestrefs(self.requested_types)
        self._check_bestrefs(bestrefs, self.requested_types)

    def test_client_dump_references(self):
        client.dump_references(self.pmap, [self.test_reference])
        self.purge_references()

    def test_client_cache_best_references(self):
        client.get_best_references(self.pmap, self.get_header())
        self.purge_references()

    def test_client_cache_best_references_for_dataset(self):
        client.cache_best_references_for_dataset(self.pmap, self.test_dataset)
        self.purge_references()

    def test_client_get_url(self):
        url = client.get_url(self.pmap, self.test_reference)

    def test_client_get_default_context(self):
        context = client.get_default_context(self.observatory)
        self.assertIn(".pmap", context)
        
    def test_client_list_mappings(self):
        client.list_mappings(server_config.observatory, "*.rmap")
        
    def getreferences(self, *args, **keys):
        # get_processing_mode is cached to avoid repeat network traffic
        heavy_client.get_processing_mode.cache.clear()
        keys = dict(keys)
        # Override other (default) context mechanisms with test context.
        if "context" not in keys:
            keys["context"] = self.pmap
        keys["observatory"] = self.observatory
        os.environ["CRDS_DOWNLOAD_MODE"] = "http"
        log.debug("Skipping getreferences download mode RPC")
        return crds.getreferences(*args, **keys)
#        os.environ["CRDS_DOWNLOAD_MODE"] = "rpc"
#        heavy_client.get_processing_mode.cache.clear()
#        return crds.getreferences(*args, **keys)

    def getrecommendations(self, *args, **keys):
        # get_processing_mode is cached to avoid repeat network traffic
        heavy_client.get_processing_mode.cache.clear()
        keys = dict(keys)
        if "context" not in keys:
            keys["context"] = self.pmap
        # Override other (default) context mechanisms with test context.
        keys["observatory"] = self.observatory
        os.environ["CRDS_DOWNLOAD_MODE"] = "http"
        log.debug("Skipping getrecommendations download mode RPC")
        return crds.getrecommendations(*args, **keys)
#        os.environ["CRDS_DOWNLOAD_MODE"] = "rpc"
#        heavy_client.get_processing_mode.cache.clear()
#        return crds.getrecommendations(*args, **keys)

    def test_getreferences_defaults(self, ignore_cache=False):
        bestrefs = self.getreferences(self.get_header(), ignore_cache=ignore_cache, context=self.pmap)
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_getreferences_defaults_imap(self, ignore_cache=False):
        bestrefs = self.getreferences(self.get_header(), ignore_cache=ignore_cache, context=self.imap)
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_getreferences_defaults_by_date(self, ignore_cache=False):
        bestrefs = self.getreferences(self.get_header(), ignore_cache=ignore_cache, context=self.pmap_date)
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_getrecommendations_defaults(self, ignore_cache=False):
        bestrefs = self.getrecommendations(self.get_header(), ignore_cache=ignore_cache, context=self.pmap)
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_getrecommendations_defaults_imap(self, ignore_cache=False):
        bestrefs = self.getrecommendations(self.get_header(), ignore_cache=ignore_cache, context=self.imap)
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_getrecommendations_defaults_by_date(self, ignore_cache=False):
        bestrefs = self.getrecommendations(self.get_header(), ignore_cache=ignore_cache, context=self.pmap_date)
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_getreferences_specific_reftypes(self):
        bestrefs = self.getreferences(self.get_header(), reftypes=self.requested_types)
        self._check_bestrefs(bestrefs, self.requested_types) 

    def test_getreferences_missing_date(self):
        header = self.get_header()
        del header[self.date_key]
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = self.getreferences(header)

    def test_getreferences_bad_date(self):
        header = self.get_header()
        header[self.date_key] = "2012-1f-23"
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = self.getreferences(header)
    
    def test_getreferences_bad_instrument(self):
        header = self.get_header()
        header[self.instr_key] = "foo"
        with self.assertRaises(crds.CrdsError):
            bestrefs = self.getreferences(header)
    
    def test_getreferences_missing_instrument(self):
        header = self.get_header()
        del header[self.instr_key]
        with self.assertRaises(crds.CrdsError):
            bestrefs = self.getreferences(header)
    
    def test_getreferences_bad_reftype(self):
        header = self.get_header()
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = self.getreferences(header, reftypes=["foo"])
    
    def test_get_server_info(self):
        info = client.get_server_info()
        assert info["operational_context"].endswith(".pmap")
        assert info["edit_context"].endswith(".pmap")
        assert re.match("\d+\.\d+(\.\d+)?(dev)?", info["crds_version"]["str"])
     
    def getreferences_fallback(self, mode):
        # First compute best refs normally, to ensure file caching
        os.environ["CRDS_MODE"] = mode
        self.test_getreferences_defaults()   # first precache
        try:
            # mess up server
            log.set_verbose(True)
            old_url = client.get_crds_server()
            client.set_crds_server("http://foo.bar")
            # attempt fallback using cached files and status
            self.test_getreferences_defaults()
        finally:
            os.environ["CRDS_MODE"] = "auto"
            client.set_crds_server(old_url)
            log.set_verbose(False)
    
    def test_getreferences_fallback_auto(self):
        self.getreferences_fallback("auto")

    def test_getreferences_fallback_local(self):
        self.getreferences_fallback("local")

    def test_getreferences_fallback_remote(self):
        with self.assertRaises(crds.CrdsError):
            self.getreferences_fallback("remote")

    def getreferences_fallup(self, mode, ignore_cache=False):
        # First compute best refs normally, to ensure file caching
        log.set_verbose(True)
        try:
            oldver = crds.__version__
            crds.__version__ = "0.0"
            os.environ["CRDS_MODE"] = mode
            self.test_getreferences_defaults(ignore_cache=ignore_cache)
        finally:
            crds.__version__ = oldver
            os.environ["CRDS_MODE"] = "auto"
            log.set_verbose(False)
    
    def test_getreferences_fallup_auto(self):
        self.getreferences_fallup("auto")

    def test_getreferences_fallup_local(self):
        self.getreferences_fallup("local")

    def test_getreferences_fallup_remote(self):
        self.getreferences_fallup("remote")

    def test_getreferences_fallup_auto_ignore(self):
        self.getreferences_fallup("auto", ignore_cache=True)

    def test_getreferences_fallup_local_ignore(self):
        self.getreferences_fallup("local", ignore_cache=True)

    def test_getreferences_fallup_remote_ignore(self):
        self.getreferences_fallup("remote", ignore_cache=True)

    def test_get_context_by_date(self):
        context = client.get_context_by_date(self.context_date)
        assert context.endswith(".pmap")
            
    def test_get_context_by_date_obs(self):
        context = client.get_context_by_date(self.context_date_obs)
        assert context.endswith(".pmap")

    def test_get_context_by_date_instr(self):
        context = client.get_context_by_date(self.context_date_instr)
        assert context.endswith(".imap")
            
    def test_get_context_by_date_filekind(self):
        context = client.get_context_by_date(self.context_date_filekind)
        assert context.endswith(".rmap")
            
    def test_get_context_by_date_fail(self):
        with self.assertRaisesRegexp(crds.CrdsError, "UnknownContextError"):
            context = client.get_context_by_date("bad time format")

    def test_get_context_by_date_edit(self):
        context = client.get_context_by_date(self.observatory + "-edit")
        assert context.endswith(".pmap")
        
    def test_get_context_by_date_operational(self):
        context = client.get_context_by_date(self.observatory + "-operational")
        assert context.endswith(".pmap")

    def test_get_required_parkeys(self):
        parkeys = client.get_required_parkeys(self.pmap)
        assert isinstance(parkeys, dict)
        for instr in parkeys:
            assert instr in imodels.INSTRUMENTS
            assert isinstance(parkeys[instr], (list,tuple))
            for parkey in parkeys[instr]:
                assert isinstance(parkey, str)
# ===========================================================================
# ===========================================================================

if server_config.observatory == "hst":
    print "testing hst"
    class HstServiceApiTest(ServiceApiBase, TestCase):
        pmap = "hst.pmap"
        pmap_date = "hst-2040-01-25T00:05:45"
        imap = "hst_wfc3.imap"
        
        observatory = server_config.observatory
        
        instr_key = "INSTRUME"
        date_key = "DATE-OBS"
        
        test_reference = 't3420177i_drk.fits'
        test_dataset = "interactive/test_data/iaai01rtq_raw.fits"
        
        requested_types = ["biasfile","darkfile"]
        
        context_date = "2050-01-01T12:00:00"
        context_date_obs = "hst-2050-01-01T12:00:00"        
        context_date_instr = "hst-acs-2050-01-01T12:00:00"
        context_date_filekind = "hst-acs-darkfile-2050-01-01T12:00:00"

        header = {
         'APERTURE': 'UVIS',
         'BINAXIS1': '1.0',
         'BINAXIS2': '1.0',
         'CCDAMP': 'ABCD',
         'CCDGAIN': '1.5',
         'CHINJECT': 'NONE',
         'DATE-OBS': '2009-07-14',
         'DETECTOR': 'UVIS',
         'FILTER': 'F555W',
         'INSTRUME': 'WFC3',
         'LTV1': '25.0',
         'LTV2': '0.0',
         'NAXIS1': '4206.0',
         'NAXIS2': '2070.0',
         'OBSMODE': 'ACCUM',
         'OBSTYPE': 'IMAGING',
         'SUBARRAY': 'F',
         'TIME-OBS': '15:56:09',
         'FLASHCUR' : 'LOW',  # just to satisfy the parameter checker.
         'SHUTRPOS' : 'A',  # just to satisfy the parameter checker.
        }
    
        def expected_references(self):
            exp = {}
            for key, value in {
             'ATODTAB': 'IREF$N9N16196I_A2D.FITS',
             'BIASFILE': 'IREF$U1R1346RI_BIA.FITS',
             'BPIXTAB': 'IREF$U5D2012LI_BPX.FITS',
             'CCDTAB': 'IREF$T291659MI_CCD.FITS',
             'CRREJTAB': 'IREF$N9I1435LI_CRR.FITS',
             'DARKFILE': 'IREF$T3420177I_DRK.FITS',
             'IDCTAB': 'IREF$x5h1320ei_idc.fits',
             'MDRIZTAB': 'IREF$UBI1853QI_MDZ.FITS',
             'OSCNTAB': 'IREF$Q911321OI_OSC.FITS',
             'PFLTFILE': 'IREF$v8816168i_pfl.fits',
            }.items():  # hack off IREF$ and switch to lower case
                exp[key.lower()] = value.lower().split("$")[1]
            return exp
        
        def test_getreferences_bad_ccdamp(self):
            header = self.get_header()
            header["CCDAMP"] = "ABCE"
            with self.assertRaises(crds.CrdsLookupError):
                bestrefs = self.getreferences(header, context=self.pmap)

        # File counts below are trip-wires with a shaky rational basis,  don't
        # loose sleep if the actual value deviates from the provided range,  just
        # take note and update.
        def test_client_get_mapping_names(self):
            mappings = client.get_mapping_names(self.pmap)
            self.failUnless(100 < len(mappings) < 200)
    
        def test_client_get_reference_names(self):
            references = client.get_reference_names(self.pmap)
            self.failUnless(11775 < len(references) < 30000)
            
# ===========================================================================

if server_config.observatory == "jwst":
    print "testing jwst"
    class JwstServiceApiTest(ServiceApiBase, TestCase):
        pmap = "jwst.pmap"
        pmap_date = "jwst-2040-01-25T00:05:45"
        imap = "jwst_miri.imap"

        observatory = server_config.observatory
    
        header = {
            "meta.instrument.type": "MIRI",
            "meta.observation.date": "2012-07-25T00:00:00",
            "meta.instrument.detector" : "MIRIMAGE",
            "meta.instrument.filter" : "F",
        }
        
        instr_key = "meta.instrument.type"
        date_key = "meta.observation.date"
        
        requested_types = ["flat"]
        
        test_reference = 'jwst_miri_flat_0001.fits'        
        test_dataset = "interactive/test_data/jw00001001001_01101_00001_MIRIMAGE_uncal.fits"
         
        context_date = "2050-01-01T12:00:00"
        context_date_obs = "jwst-2050-01-01T12:00:00"        
        context_date_instr = "jwst-miri-2050-01-01T12:00:00"
        context_date_filekind = "jwst-miri-flat-2050-01-01T12:00:00"

        def expected_references(self):
            return {
                    "flat" : "jwst_miri_flat_0001.fits",
            }
