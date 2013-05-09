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
        'crds.server.jsonapi',
        'crds.server.jsonapi.templatetags',
        'crds.server.jpoll',
        'crds.server.jpoll.templatetags',
        'crds.server.utils',
        'crds.server.stats',
        
        'crds.server.fileupload',
        'crds.server.fileupload.templatetags',
        
        'crds.server.locking',
        'crds.server.locking.management',
        'crds.server.locking.management.commands',
        'crds.server.locking.migrations',
        ],

      package_dir = {
        'crds.server':'.',

        'crds.server.jsonapi':'./jsonapi',
        'crds.server.jsonapi.templatetags':'./jsonapi/templatetags',

        'crds.server.jpoll':'./jpoll',
        # 'crds.server.jpoll.templatetags':'./jpoll/templatetags',        

        'crds.server.interactive':'./interactive',
        'crds.server.interactive.templatetags':'./interactive/templatetags',
        
        'crds.server.utils' : './utils',
        'crds.server.stats' : './stats',
        
        'crds.server.fileupload' : './fileupload',
        'crds.server.fileupload.templatetags' : './fileupload/templatetags',

        'crds.server.locking' : './locking',
        'crds.server.locking.management' : './locking/management',
        'crds.server.locking.management.commands' : './locking/management/commands',
        'crds.server.locking.migrations' : './locking/migrations',

        },

      package_data = {
        '': [ "templates/*.html",

              "interactive/*.dat",
              "interactive/templates/*.html",  
              "interactive/static/*.css",  
              "interactive/static/*.ico",  
              "interactive/static/*.png",  
              "interactive/static/users_guide/*.html", 
              "interactive/static/users_guide/*.js", 
              "interactive/static/users_guide/_static/*.css", 
              "interactive/static/users_guide/_static/*.gif", 
              "interactive/static/users_guide/_static/*.png", 
              "interactive/static/users_guide/_images/*.png", 
              "interactive/static/users_guide/_static/*.js", 
              "interactive/static/users_guide/_sources/*.txt", 
              "interactive/static/*.js", 
              "interactive/static/jquery-ui/css/smoothness/*.css",
              "interactive/static/jquery-ui/css/smoothness/images/*.png",
              "interactive/static/jquery-ui/js/*.js",
              
              "jsonapi/templates/*.html",  

              "jpoll/templates/*.html",  
              "jpoll/static/*.js",  

              "fileupload/templates/*.html",  
              "fileupload/templates/fileupload/*.html",  
              "fileupload/static/css/*.css",
              "fileupload/static/img/*.png",
              "fileupload/static/img/*.gif",
              "fileupload/static/js/*.js",
              "fileupload/templates/*.html",
              "fileupload/templates/fileupload/*.html",
             ],
        }
    )
