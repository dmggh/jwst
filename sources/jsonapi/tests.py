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

from crds import pysh, rmap, selectors, log, pysh
import crds.client as client
import crds.server.config as server_config
import crds.heavy_client as heavy_client

HERE = os.path.dirname(__file__) or "."
CRDS_PATH = os.environ["CRDS_PATH"] = server_config.install_root + "/test"
pysh.sh("rm -rf ${CRDS_PATH}", raise_on_error=True)
pysh.sh("mkdir -p ${CRDS_PATH}", raise_on_error=True)
test_maps = CRDS_PATH + "/mappings"
test_refs = CRDS_PATH + "/references"
CRDS_REAL_MAPPATH = os.environ["CRDS_MAPPATH"]
pysh.sh("cp -r ${CRDS_REAL_MAPPATH} ${test_maps}")
CRDS_MAPPATH = os.environ["CRDS_MAPPATH"] = test_maps
CRDS_REFPATH = os.environ["CRDS_REFPATH"] = test_refs

client.set_crds_server(server_config.CRDS_URL)

class ServiceApiBase(object):

    def get_header(self):
        return dict(self.header)
    
    def expected_references(self):
        raise NotImplementedError("ServiceApiTest is abstract: subclass and define expected_references().")

    def get_bestrefs(self, reftypes=[]):
        header = self.get_header()
        return client.get_best_references(self.pmap, header, reftypes)

    def purge_mappings(self):
        pysh.sh("rm -rf " + CRDS_PATH)        
        
    def purge_references(self):
        pysh.sh("rm -rf " + CRDS_PATH)

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

    def test_client_get_reference_url(self):
        url = client.get_reference_url(self.pmap, self.test_reference)

    def test_client_get_default_context(self):
        context = client.get_default_context(self.observatory)
        self.assertIn(".pmap", context)
        
    def getreferences(self, *args, **keys):
        keys["observatory"] = self.observatory
        return crds.getreferences(*args, **keys)

    def test_getreferences_defaults(self, ignore_cache=False):
        bestrefs = self.getreferences(self.get_header(), ignore_cache=ignore_cache)
        self._check_bestrefs(bestrefs, self.expected_references().keys())

    def test_getreferences_specific_reftypes(self):
        bestrefs = self.getreferences(
            self.get_header(), reftypes=self.requested_types, 
            context=self.pmap)
        self._check_bestrefs(bestrefs, self.requested_types) 

    def test_getreferences_missing_date(self):
        header = self.get_header()
        del header[self.date_key]
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = self.getreferences(header, context=self.pmap)

    def test_getreferences_bad_date(self):
        header = self.get_header()
        header[self.date_key] = "2012-1f-23"
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = self.getreferences(header, context=self.pmap)
    
    def test_getreferences_bad_instrument(self):
        header = self.get_header()
        header[self.instr_key] = "foo"
        with self.assertRaises(crds.CrdsError):
            bestrefs = self.getreferences(header, context=self.pmap)
    
    def test_getreferences_missing_instrument(self):
        header = self.get_header()
        del header[self.instr_key]
        with self.assertRaises(crds.CrdsError):
            bestrefs = self.getreferences(header, context=self.pmap)
    
    def test_getreferences_bad_reftype(self):
        header = self.get_header()
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = self.getreferences(header, context=self.pmap, reftypes=["foo"])
    
    def test_get_server_info(self):
        info = client.get_server_info()
        assert info["operational_context"].endswith(".pmap")
        assert info["edit_context"].endswith(".pmap")
        assert re.match("\d+\.\d+(\.\d+)?(dev)?", info["crds_version"]["str"])
     
    def getreferences_fallback(self, mode):
        # First compute best refs normally, to ensure file caching
        heavy_client.get_processing_mode.cache.clear() 
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
            heavy_client.get_processing_mode.cache.clear() 
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
        crds_mappath = crds.config.get_crds_mappath()
        crds_refpath = crds.config.get_crds_refpath()
        try:
            heavy_client.get_processing_mode.cache.clear() 
            oldver = crds.__version__
            crds.__version__ = "0.0"
            os.environ["CRDS_MODE"] = mode
            self.test_getreferences_defaults(ignore_cache=ignore_cache)
        finally:
            heavy_client.get_processing_mode.cache.clear() 
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

# ===========================================================================
if server_config.observatory == "hst":
    print "testing hst"
    class HstServiceApiTest(ServiceApiBase, TestCase):
        pmap = "hst.pmap"
        
        observatory = server_config.observatory
        
        instr_key = "INSTRUME"
        date_key = "DATE-OBS"
        
        test_reference = 't3420177i_drk.fits'
        test_dataset = "interactive/test_data/iaai01rtq_raw.fits"
        
        requested_types = ["biasfile","darkfile"]
        
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
             'IDCTAB': 'IREF$w2r1956ri_idc.fits',
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
            self.failUnless(100 < len(mappings) < 120)
    
        def test_client_get_reference_names(self):
            references = client.get_reference_names(self.pmap)
            self.failUnless(11775 < len(references) < 20000)


# ===========================================================================

if server_config.observatory == "jwst":
    print "testing jwst"
    class JwstServiceApiTest(ServiceApiBase, TestCase):
        pmap = "jwst.pmap"
        observatory = server_config.observatory
    
        header = {
            "meta.instrument.type": "MIRI",
            "meta.observation.date": "2012-07-25T00:00:00",
        }
        
        instr_key = "meta.instrument.type"
        date_key = "meta.observation.date"
        
        requested_types = ["flat"]
        
        test_reference = 'jwst_miri_flat_0001.fits'        
        test_dataset = "interactive/test_data/jwst_fake_raw.fits"
        
        def expected_references(self):
            return {
                    "flat" : "jwst_miri_flat_0001.fits",
            }
