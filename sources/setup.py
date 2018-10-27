#!/usr/bin/env python
import os.path

from distutils.core import setup

PACKAGES = [
    'crds_server',
    'crds_server.interactive',
    'crds_server.interactive.templatetags',
    'crds_server.interactive.migrations',

    'crds_server.jsonapi',
    'crds_server.jsonapi.templatetags',

    'crds_server.jpoll',
    'crds_server.jpoll.templatetags',

    'crds_server.xhst',
    'crds_server.xjwst',
    
    'crds_server.fileupload',
    'crds_server.fileupload.templatetags',
    
    'crds_server.locking',
    'crds_server.locking.management',
    'crds_server.locking.management.commands',

    # 'crds_server.forms',
    # 'crds_server.forms.migrations',
    ]

PACKAGE_DIR = {
    'crds_server':'.',
    
    'crds_server.xhst' : './xhst', 
    'crds_server.xjwst' : './xjwst',     
    
    'crds_server.jsonapi':'./jsonapi',
    'crds_server.jsonapi.templatetags':'./jsonapi/templatetags',
    
    'crds_server.jpoll':'./jpoll',
    # 'crds_server.jpoll.templatetags':'./jpoll/templatetags',        
    
    'crds_server.interactive':'./interactive',
    'crds_server.interactive.migrations':'./interactive/migrations',
    'crds_server.interactive.templatetags':'./interactive/templatetags',
    
    'crds_server.fileupload' : './fileupload',
    'crds_server.fileupload.templatetags' : './fileupload/templatetags',
    
    'crds_server.locking' : './locking',
    'crds_server.locking.management' : './locking/management',
    'crds_server.locking.management.commands' : './locking/management/commands',

    # 'crds_server.forms':'./forms',
    # 'crds_server.forms.migrations':'./forms/migrations',
    # 'crds_server.forms.templatetags':'./forms/templatetags',

    }

PACKAGE_DATA = {
    '': [ 
        "templates/*",
        "interactive/templates/*",
        "interactive/templates/registration/*",
        "interactive/*.dat",

        "xhst/*.bdf",

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

        # "forms/templates/*",
        ],
    }

static_files = ["static_dirs.txt"]
for root, dirs, files in os.walk("static"):
    static_files.extend([os.path.join(root, file) for file in files])
    if '.svn' in dirs:
        dirs.remove('.svn')  # don't visit .svn

PACKAGE_DATA[''].extend(static_files)

# DATA_FILES = [("", static_files)]

setup(name="crds_server",
      version= "7.2.9",
      description="CRDS server,  JWST B7.2 + CAL 0.12.1(?)",
      author="Todd Miller",
      author_email="jmiller@stsci.edu",

      packages=PACKAGES,
      package_dir=PACKAGE_DIR,
      package_data=PACKAGE_DATA,

      # data_files=DATA_FILES,
    )
