"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
import sys
import os
import os.path

from django.test import TestCase

import crds.pysh as pysh
import crds.client.api as api
import crds.hst.gentools.lookup as lookup

HERE = os.path.dirname(__file__) or "."

lookup.load_header_cache()

class ServiceApiTest(TestCase):
    def setUp(self):
        self.api = api
        self.context = "hst.pmap"

    def get_header(self):
        header = lookup.get_header_union("../../testdata/wfc3/howard/iaai01rtq_raw.fits")
        return header

    def get_bestrefs(self):
        header = self.get_header()
        os.environ["CRDS_REFPATH"] = HERE + "/test_references"
        return api.get_best_refs(self.context, header)

    def purge_mappings(self):
        pysh.sh("rm -rf " + HERE + "/test_mappings")        
        
    def purge_references(self):
        pysh.sh("rm -rf " + HERE + "/test_references")

    def test_api_get_mapping_names(self):
        mappings = self.api.get_mapping_names(self.context)
        self.failUnlessEqual(len(mappings), 72)
        
    def test_api_get_reference_names(self):
        references = self.api.get_reference_names(self.context)
        self.failUnlessEqual(len(references), 5719)
        
    def test_api_cache_mappings(self):
        os.environ["CRDS_MAPPATH"] = HERE + "/test_mappings" 
        self.api.cache_mappings(self.context)
        self.purge_mappings()
        
    def test_api_get_bestrefs(self):
        bestrefs = self.get_bestrefs()
        for key,value in bestrefs.items():
            if key in self.get_header():
                self.assertEqual(header[key], value)
                
    def test_api_cache_references(self):
        bestrefs = {'idctab': 'uab1537bi_idc.fits', 'darkfile': 't3420177i_drk.fits'}
        api.cache_references(self.context, bestrefs)
        self.purge_references()

    def test_api_dump_references(self):
        bestrefs = {'idctab': 'uab1537bi_idc.fits', 'darkfile': 't3420177i_drk.fits'}
        api.dump_references(self.context, bestrefs.values())
        self.purge_references()
        
    def test_api_get_reference_url(self):
        url = api.get_reference_url(self.context, 'uab1537bi_idc.fits')

    def test_api_get_mapping_url(self):
        url = api.get_mapping_url(self.context, "hst_acs.imap")

