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

HERE = os.path.dirname(__file__) or "."

os.environ["CRDS_PATH"] = CRDS_PATH = HERE + "/crds"

client.set_crds_server(server_config.CRDS_URL)

class ServiceApiTest(TestCase):
    def setUp(self):
        self.context = "hst.pmap"

    def get_header(self):
        # crds.client.get_minimum_header("hst.pmap", "../../../testdata/wfc3/howard/iaai01rtq_raw.fits")
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
        return header
    
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

    def get_bestrefs(self, reftypes=[]):
        header = self.get_header()
        return client.get_best_references(self.context, header, reftypes)

    def purge_mappings(self):
        pysh.sh("rm -rf " + CRDS_PATH)        
        
    def purge_references(self):
        pysh.sh("rm -rf " + CRDS_PATH)

    # File counts below are trip-wires with a shaky rational basis,  don't
    # loose sleep if the actual value deviates from the provided range,  just
    # take note and update.
    def test_client_get_mapping_names(self):
        mappings = client.get_mapping_names(self.context)
        self.failUnless(100 < len(mappings) < 120)
        
    def test_client_get_reference_names(self):
        references = client.get_reference_names(self.context)
        self.failUnless(11775 < len(references) < 20000)
        
    def test_client_dump_mappings(self):
        client.dump_mappings(self.context)
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
        bestrefs = self.get_bestrefs(["biasfile","darkfile"])
        self._check_bestrefs(bestrefs, ["biasfile", "darkfile"])
                
    def test_client_dump_references(self):
        client.dump_references(self.context, ['t3420177i_drk.fits'])
        self.purge_references()
        
    def test_client_cache_best_references(self):
        client.get_best_references(self.context, self.get_header())
        self.purge_references()
        
    def test_client_cache_best_references_for_dataset(self):
        client.cache_best_references_for_dataset(self.context, "interactive/test_data/iaai01rtq_raw.fits")
        self.purge_references()
        
    def test_client_get_reference_url(self):
        url = client.get_reference_url(self.context, 't3420177i_drk.fits')

    def test_client_get_default_context(self):
        context = client.get_default_context("hst")
        self.assertIn(".pmap", context)
        
    def test_getreferences_defaults(self, ignore_cache=False):
        bestrefs = crds.getreferences(self.get_header(), ignore_cache=ignore_cache)
        self._check_bestrefs(bestrefs, self.expected_references().keys())
        
    def test_getreferences_specific_reftypes(self):
        bestrefs = crds.getreferences(
            self.get_header(), reftypes=["biasfile","darkfile"], 
            context="hst.pmap")
        self._check_bestrefs(bestrefs, ["biasfile","darkfile"]) 
        
    def test_getreferences_missing_date(self):
        header = self.get_header()
        del header["DATE-OBS"]
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = crds.getreferences(header, context="hst.pmap")

    def test_getreferences_bad_date(self):
        header = self.get_header()
        header["DATE-OBS"] = "2012-1f-23"
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = crds.getreferences(header, context="hst.pmap")
    
    def test_getreferences_bad_ccdamp(self):
        header = self.get_header()
        header["CCDAMP"] = "ABCE"
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = crds.getreferences(header, context="hst.pmap")
    
    def test_getreferences_bad_instrument(self):
        header = self.get_header()
        header["INSTRUME"] = "foo"
        with self.assertRaises(crds.CrdsError):
            bestrefs = crds.getreferences(header, context="hst.pmap")
    
    def test_getreferences_missing_instrument(self):
        header = self.get_header()
        del header["INSTRUME"]
        with self.assertRaises(crds.CrdsError):
            bestrefs = crds.getreferences(header, context="hst.pmap")
    
    def test_getreferences_bad_reftype(self):
        header = self.get_header()
        with self.assertRaises(crds.CrdsLookupError):
            bestrefs = crds.getreferences(header, context="hst.pmap", reftypes=["foo"])
    
    def test_get_server_info(self):
        info = client.get_server_info()
        assert info["operational_context"].endswith(".pmap")
        assert info["edit_context"].endswith(".pmap")
        assert re.match("\d+\.\d+(\.\d+)?(dev)?", info["crds_version"]["str"])
     
    def getreferences_fallback(self, mode):
        # First compute best refs normally, to ensure file caching
        os.environ["CRDS_MODE"] = mode
        os.environ["CRDS_OBSERVATORY"] = "hst"
        self.test_getreferences_defaults()
        # mess up server
        try:
            log.set_verbose(True)
            old_url = client.get_crds_server()
            client.set_crds_server("http://foo.bar")
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

    # XXX TODO:  setting crds.__version__ doesn't work in this context.
    def getreferences_fallup(self, mode, ignore_cache=False):
        # First compute best refs normally, to ensure file caching
        log.set_verbose(True)
        try:
            oldver = crds.__version__
            crds.__version__ == "0.0"
            os.environ["CRDS_MODE"] = mode
            os.environ["CRDS_OBSERVATORY"] = "hst"
            crds_mappath = crds.config.get_crds_mappath()
            crds_refpath = crds.config.get_crds_refpath()
            pysh.sh("chmod -R 777 ${crds_mappath} ${crds_refpath}")
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

    def test_getreferences_fallup_auto(self):
        self.getreferences_fallup("auto", ignore_cache=True)

    def test_getreferences_fallup_local(self):
        self.getreferences_fallup("local", ignore_cache=True)

    def test_getreferences_fallup_remote(self):
        self.getreferences_fallup("remote", ignore_cache=True)

