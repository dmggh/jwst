"""S/W Version management code derived from the module of the same name
in pyetc.
"""
import sys
import os
import re
import os.path

from crds.core import pysh

MODULE_LIST = (
    'django',
    'matplotlib',
    'numpy',
    # 'scipy',

    'crds',
    'crds_server',

    'pyodbc',
    'jsonrpc',

    'astropy',
    'jwst.datamodels',
    'asdf',

    'parsley',
    'yaml'
    )

def get_all_versions( mods = MODULE_LIST ):
    """Return a dictionary of version dictionaries for all modules named
    in sequence `mods`.
    """
    # ... all the relevant python modules
    v_dict = { modname:get_version(modname) for modname in mods }

    # ... the python interpreter
    v_dict['python'] = get_python_version()
    v_dict['linux']  = get_linux_version()
    v_dict['mod_wsgi']  = get_mod_wsgi_version()
    v_dict['apache'] = get_apache_version()
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
        return { key:"missing" for key in ["str", "rev", "svnurl", "file"]}

    # try all the "standard" ways for it to say a version number
    try:
        ans = mod.__version__
    except AttributeError:
        try:
            ans = mod.VERSION
        except AttributeError:
            try:
                ans = mod.version
                if not isinstance(mod.version, str):
                    ans = ans()
            except AttributeError:
                try:
                    import pkg_resources;  
                    ans = pkg_resources.require(modname)[0].version
                except Exception:
                    ans = 'unknown'

    # some modules won't give you a string
    ans = str(ans)

    # where is it in the filesystem?
    try :
        filename = mod.__file__  # WARNING:  overriding builtin function file()
    except AttributeError :
        filename = ''

    # extract svn version from STScI code
    try:
        mod = dynamic_import("%s.svn_version" % modname)
        rev = mod.__svn_version__
        url = mod.__full_svn_info__ .split('URL: ')[1].split('\n')[0].split("/")[-1]
    except Exception:
        try:
            mod = dynamic_import("%s.git_version" % modname)
            rev = mod.__version__
            url = mod.__full_version_info__ .split('branch: ')[1].split('\n')[0]
        except Exception:
            rev = ''
            url = ''

    vers = {
        'str'   : ans,
        'rev'   : rev,
        'svnurl': url,
        'file'  : filename
        }
    return vers



def get_python_version():
    """Return information about Python version"""
    return {
        'str'   : sys.version.split(' ')[0],
        'rev'   : '',
        'svnurl': '',
        'file'  : sys.prefix
    }

def get_linux_version():
    """Return information about Linux kernel version"""
    try:
        version = pysh.out("/bin/uname -a").split()[2]
    except Exception:
        version = "unknown"
    return {
        'str'   : version,
        'rev'   : '',
        'svnurl': '',
        'file'  : '',
    }

def get_mod_wsgi_version():
    """Return information about mod_wsgi version"""
    try:  #  lib/python.xx/site-packages/crds_server
        module_dir = os.path.join(os.environ["CRDS"], "lib")
        version = pysh.lines('cd %s;  /usr/bin/strings mod_wsgi.so | grep -w -A 1 "wsgi_init"' % module_dir)[1]
    except Exception:
        version = "unknown"
    return {
        'str'   : version,
        'rev'   : '',
        'svnurl': '',
        'file'  : '',
    }

def get_apache_version():
    """Return information about mod_wsgi version

    /sbin/httpd -v
    Server version: Apache/2.4.6 (Red Hat Enterprise Linux)
    Server built:   Mar  8 2017 05:09:47
    """
    try:
        version = pysh.lines("/sbin/httpd -v")[0].split("/")[1].split(" ")[0]
    except Exception:
        version = "unknown"
    return {
        'str'   : version,
        'rev'   : '',
        'svnurl': '',
        'file'  : '',
    }

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
    namespace = {}
    exec("import " + package + " as module", namespace, namespace)
    return namespace["module"]

