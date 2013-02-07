"""S/W Version management code derived from the module of the same name
in pyetc.
"""

from __future__ import division

import os
import sys
import datetime
import hashlib
import re

from django.db import connection
from django.shortcuts import render_to_response
from django.http import HttpResponse

import crds.server.config as config
import crds.log as log

MODULE_LIST = (
    'django',
    'matplotlib',
    'numpy',
    # 'scipy',
    
    'crds',
    'crds.server',
    'crds.client',
    'crds.hst',
    'crds.jwst',
    
    'pyodbc',
    'jsonrpc',
    
    'pyfits',
    'jwstlib.models',
    )

def get_all_versions( mods = MODULE_LIST ):
    """Return a dictionary of version dictionaries for all modules named 
    in sequence `mods`.
    """
    # ... all the relevant python modules
    v_dict = { modname:get_version(modname) for modname in mods }

    # ... the python interpreter
    v_dict['python'] = {
        'str'   : sys.version.split(' ')[0],
        'rev'   : '',
        'svnurl': '',
        'file'  : sys.prefix
    }

    return v_dict


#####
#
# Do all the things we have to do to identify the version of a python module
#

def get_version(modname):
    """Return dictionary of version info for module named `modname`.
    """
    try:
        mod = dynamic_import(modname)
    except ImportError:
        return { key:"missing" for key in ["str","rev","svnurl","file"]}
    
    # try all the "standard" ways for it to say a version number
    try:
        ans = mod.__version__
    except AttributeError:
        try:
            ans = mod.VERSION
        except AttributeError:
            try:
                ans = mod.version
                if not isinstance(mod.version, (str, unicode)):
                    ans = ans()
            except AttributeError:
                ans = 'unknown'

    # some modules won't give you a string
    ans = str(ans)

    # where is it in the filesystem?
    try :
        file = mod.__file__  # WARNING:  overriding builtin function file()
    except AttributeError :
        file = ''

    # extract svn version from STScI code
    try:
        mod = dynamic_import("%s.svn_version" % modname)
        svnrev = mod.__svn_version__
        svnurl = mod.__full_svn_info__ .split('URL: ')[1].split('\n')[0]
    except Exception, exc:
        svnrev = ''
        svnurl = ''

    vers = {
        'str'   : ans,
        'rev'   : svnrev,
        'svnurl': svnurl,
        'file'  : file
        }
    return vers


# Basically permit dotted identifiers, not worrying about invalid
# package specifiers or what is being imported, but ensuring that
# nothing more exotic can possibly be exec'ed.
PACKAGE_RE = re.compile("[A-Za-z_0-9.]+")

def dynamic_import(package):
    """imports a module specified by string `package` which is
    not known until runtime.

    Returns a module/package.

    The purpose of this function is to concentrate a number of uses
    of the "exec" statement in once place where it can be policed
    for security reasons.
    """
    if not PACKAGE_RE.match(package):
        raise ImportError("Invalid dynamic import " + repr(package))
    exec "import " + package + " as m" in locals(), locals()
    return m

