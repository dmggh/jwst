"""These tests exercise the functions in the CRDS client API.
"""
import sys
import os
import os.path

from django.test import TestCase

import crds
from crds import pysh, rmap
import crds.client as client
import crds.server.interactive.models as imodels

HERE = os.path.dirname(__file__) or "."

os.environ["CRDS_REFPATH"] = HERE + "/test_references"

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
        pysh.sh("rm -rf " + HERE + "/test_mappings")        
        
    def purge_references(self):
        pysh.sh("rm -rf " + HERE + "/test_references")

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
        os.environ["CRDS_MAPPATH"] = HERE + "/test_mappings" 
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
        
    def test_getreferences_1(self):
        """default reftypes and context to None"""
        bestrefs = crds.getreferences(self.get_header())
        self._check_bestrefs(bestrefs, self.expected_references().keys())
        
    def test_getreferences_2(self):
        """default reftypes and context to None"""
        bestrefs = crds.getreferences(
            self.get_header(), reftypes=["biasfile","darkfile"], 
            context="hst.pmap")
        self._check_bestrefs(bestrefs, ["biasfile","darkfile"]) 
    
#    def test_getreferences_3(self):
#        """with parameters/header as dataset file."""
#        bestrefs = crds.getreferences("interactive/test_data/iaai01rtq_raw.fits")
#        self._check_bestrefs(bestrefs, self.expected_references().keys())


