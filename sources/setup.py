#!/usr/bin/env python
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
import os.path

from distutils.core import setup

PACKAGES = [
    'crds.server',
    'crds.server.interactive',
    'crds.server.interactive.templatetags',
    'crds.server.interactive.migrations',

    'crds.server.jsonapi',
    'crds.server.jsonapi.templatetags',

    'crds.server.jpoll',
    'crds.server.jpoll.templatetags',

    'crds.server.xhst',
    'crds.server.xjwst',
    
    'crds.server.fileupload',
    'crds.server.fileupload.templatetags',
    
    'crds.server.locking',
    'crds.server.locking.management',
    'crds.server.locking.management.commands',

    'crds.server.forms',
    'crds.server.forms.migrations',
    ]

PACKAGE_DIR = {
    'crds.server':'.',
    
    'crds.server.xhst' : './xhst', 
    'crds.server.xjwst' : './xjwst',     
    
    'crds.server.jsonapi':'./jsonapi',
    'crds.server.jsonapi.templatetags':'./jsonapi/templatetags',
    
    'crds.server.jpoll':'./jpoll',
    # 'crds.server.jpoll.templatetags':'./jpoll/templatetags',        
    
    'crds.server.interactive':'./interactive',
    'crds.server.interactive.migrations':'./interactive/migrations',
    'crds.server.interactive.templatetags':'./interactive/templatetags',
    
    'crds.server.fileupload' : './fileupload',
    'crds.server.fileupload.templatetags' : './fileupload/templatetags',
    
    'crds.server.locking' : './locking',
    'crds.server.locking.management' : './locking/management',
    'crds.server.locking.management.commands' : './locking/management/commands',

    'crds.server.forms':'./forms',
    'crds.server.forms.migrations':'./forms/migrations',
    'crds.server.forms.templatetags':'./forms/templatetags',

    }

PACKAGE_DATA = {
    '': [ 
        "templates/*",
        "interactive/templates/*",
        "interactive/templates/registration/*",
        "interactive/*.dat",

        "xhst/*.dat",
        "xjwst/*.dat",

        "xhst/*.json",
        "xjwst/*.json",

        "interactive/test_data/*",
        
        "jsonapi/templates/*.html",  
          
        "jpoll/templates/*.html",  
        "jpoll/templates/jpoll/*.html",  
        "jpoll/static/*.js",  
        
        "fileupload/templates/*.html",  
        "fileupload/templates/fileupload/*.html",  
        "fileupload/static/css/*.css",
        "fileupload/static/img/*.png",
        "fileupload/static/img/*.gif",
        "fileupload/static/js/*.js",
        "fileupload/static/js/*.js.map",
        "fileupload/templates/*.html",
        "fileupload/templates/fileupload/*.html",

        "forms/templates/*",
        ],
    }

static_files = ["static_dirs.txt"]
for root, dirs, files in os.walk("static"):
    static_files.extend([os.path.join(root, file) for file in files])
    if '.svn' in dirs:
        dirs.remove('.svn')  # don't visit .svn

PACKAGE_DATA[''].extend(static_files)

# DATA_FILES = [("", static_files)]

setup(name="crds.server",
      version= "7.2.0",
      description="Python based Calibration Reference Data System,  best reference file web service",
      author="Todd Miller",
      author_email="jmiller@stsci.edu",

      packages=PACKAGES,
      package_dir=PACKAGE_DIR,
      package_data=PACKAGE_DATA,

      # data_files=DATA_FILES,
    )
