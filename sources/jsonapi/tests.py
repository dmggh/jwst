"""These tests exercise the functions in the CRDS client API.
"""
import sys
import os
import os.path

from django.test import TestCase

import crds.pysh as pysh
import crds.client as client

HERE = os.path.dirname(__file__) or "."

class ServiceApiTest(TestCase):
    def setUp(self):
        self.context = "hst.pmap"

    def get_header(self):
        # header = crds.client.api.get_minimum_header(
        #    "../../testdata/wfc3/howard/iaai01rtq_raw.fits")
        header = {
         'APERTURE': 'UVIS',
         'BINAXIS1': '1.0',
         'BINAXIS2': '1.0',
         'CCDAMP': 'ABCD',
         'CCDGAIN': '1.5',
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
        # 'ATODTAB': 'IREF$N9N16196I_A2D.FITS',  # disabled in CDBS web table
         'BIASFILE': 'IREF$U1R1346RI_BIA.FITS',
         'BPIXTAB': 'IREF$U5D2012LI_BPX.FITS',
         'CCDTAB': 'IREF$T291659MI_CCD.FITS',
         'CRREJTAB': 'IREF$N9I1435LI_CRR.FITS',
         'DARKFILE': 'IREF$T3420177I_DRK.FITS',
         'IDCTAB': 'IREF$v5r1512gi_idc.fits',
         'MDRIZTAB': 'IREF$UBI1853QI_MDZ.FITS',
         'OSCNTAB': 'IREF$Q911321OI_OSC.FITS',
         'PFLTFILE': 'IREF$v8816168i_pfl.fits',
        }.items():  # hack off IREF$ and switch to lower case
            exp[key.lower()] = value.lower().split("$")[1]
        return exp

    def get_bestrefs(self):
        header = self.get_header()
        os.environ["CRDS_REFPATH"] = HERE + "/test_references"
        return client.get_best_references(self.context, header)

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
        
    def test_client_get_bestrefs(self):
        bestrefs = self.get_bestrefs()
        for key, value in self.expected_references().items():
            self.assertIn(key, bestrefs)
            self.assertEqual(bestrefs[key], value)
                
    def test_client_dump_references(self):
        client.dump_references(self.context, ['t3420177i_drk.fits'])
        self.purge_references()
        
    def test_client_cache_best_references(self):
        client.get_best_references(self.context, self.get_header())
        self.purge_references()
        
    def test_client_cache_best_references_for_dataset(self):
        client.cache_best_references_for_dataset(self.context, "interactive/test_data/j8bt05njq_raw.fits")
        self.purge_references()
        
    def test_client_get_reference_url(self):
        url = client.get_reference_url(self.context, 't3420177i_drk.fits')

    def test_client_get_mapping_url(self):
        url = client.get_mapping_url(self.context, "hst_acs.imap")
        
