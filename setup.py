#!/usr/bin/env python
from distutils.core import setup

import pytools.stsci_distutils_hack as dh
f = open('svn_version.py', 'w' )
f.write("__svn_version__ = '%s'\n" % dh.__get_svn_rev__('.'))
f.write("\n__full_svn_info__ = '''\n%s'''\n\n" % dh.__get_full_info__('.'))
f.close()

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
