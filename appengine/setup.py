#!/usr/bin/env python
from distutils.core import setup

setup(name="crds.server",
      version= "0.1",
      description="Python based Calibration Reference Data System,  best reference file web service",
      author="Todd Miller",
      author_email="jmiller@stsci.edu",

      packages=[
        'crds.server',
        'crds.server.interactive',
        'crds.server.interactive.templatetags',
        'crds.server.lookup',
        'crds.server.lookup.templatetags'
        ],

      package_dir = {
        'crds.server':'.',
        'crds.server.lookup':'./lookup',
        'crds.server.lookup.templatetags':'./lookup/templatetags',
        'crds.server.interactive':'./interactive',
        'crds.server.interactive.templatetags':'./interactive/templatetags',
        },

      package_data = {
        '': [ "templates/*.html",  ],
        }
    )
