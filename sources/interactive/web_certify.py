"""Functions supporting certification of files and presenting the cert output to the web.
Aside from output capture to strings,  handles weird web naming/path issues and temporaries...
while making the output look sane.
"""

import os.path

from crds import rmap, certify
from crds import CrdsError

from . import models
from .common import capture_output, srepr

def certify_file_list(upload_tuples, check_references=True, context=None, compare_old_reference=False):
    """Certify the list of `upload_tuples` specifying uploaded files.
    
    If `check_references` is True,  make sure references referred to by mappings exist.
    
    If `context` is specified, verify references and mappings relative to the corresponding
    files in that context.
    
    If `compare_old_references` is True,  compare references to the corresponding files in the context.
    
    Returns disposition,  sorted({uploaded_name :  (status, <certify_output>) }.items())
    
    where disposition is either "" or "bad files" and used to suppress confirmation.
    """
    filemap = models.get_fileblob_map(models.OBSERVATORY)
    certify_results = {}
    disposition = ""
    for (original_name, upload_path) in upload_tuples:
        # In order to capture output easily,  run as subprocess...
        status, output = captured_certify(original_name, upload_path, 
            check_references=check_references, filemap=filemap, context=context, 
            compare_old_reference=compare_old_reference)
        certify_results[original_name] = status, output
        if status == "Failed.":
            disposition = "bad files"
    return disposition, sorted(certify_results.items())

def captured_certify(original_name, uploaded_path, check_references=True, filemap=None, context=None,
                     compare_old_reference=False):
    """Run certify capturing and categorizing the output.
    
    Returns ("OK|"Warnings"|"Failed", certify_output) 
    """
    output = _captured_certify(original_name, uploaded_path, filemap, context, compare_old_reference)[1]
    if ": ERROR" not in output:
        if ": WARNING" not in output:
            status = "OK"
        else:
            status = "Warnings"
    else:
        status = "Failed."
    if status != "Failed.":    # if OK the rmap should load...
        if check_references and rmap.is_mapping(original_name):
            if filemap is None:
                filemap = models.get_fileblob_map(models.OBSERVATORY)
            ctx = rmap.fetch_mapping(uploaded_path)
            for ref in ctx.reference_names():
                if ref not in filemap:
                    output += "ERROR: Reference " + srepr(ref) + " in " + \
                            srepr(original_name) + " is not known to CRDS.\n"
                    status = "Failed."
                    
    return status, output

@capture_output
def _captured_certify(original_name, uploaded_path, filemap=None, context=None, compare_old_reference=False):
    """Run  crds.certify_files on `uploaded_path` and capture it's stdout/stderr."""
    certify.certify_files([uploaded_path], context=context, dump_provenance=True, check_references=False, 
                          is_mapping=rmap.is_mapping(original_name), trap_exceptions=True)

def get_blacklist_file_list(upload_tuples, all_files):
    """Return the mapping of blacklist status and blacklisted_by list for the
    given `uploaded_tuples` with respect to `all_files`.
    
    Returns { original_name :  (blacklist_status, blacklisted_by), ... }
    """
    blacklist_results = {}
    for (original_name, upload_path) in upload_tuples:
        try:
            blacklisted_by = get_blacklists(
                original_name, upload_path, ignore_self=False, files=all_files)
        except Exception:
            blacklisted_by = []
            blacklist_status = "Error"
        else:        
            if blacklisted_by:
                blacklist_status = "Blacklisted"
            else:
                blacklist_status = "OK"
        blacklist_results[original_name] = (blacklist_status, blacklisted_by)
    return blacklist_results

def get_blacklists(basename, certifypath, ignore_self=True, files=None):
    """Return a list of the files referenced by `basename` which are
    blacklisted.
    """
    basename = str(basename)
    if rmap.is_mapping(basename):
        blacklisted_by = set()
        try:
            mapping = rmap.fetch_mapping(certifypath)
        except Exception, exc:
            raise CrdsError("Error loading " + srepr(basename) + " : " + str(exc))
        if files is None:
            files = models.get_fileblob_map(mapping.observatory)
        
        for child in mapping.mapping_names() + mapping.reference_names():       
            if ignore_self and child == os.path.basename(certifypath): 
                continue
            if child not in files:   # Unknown file,  what to do?
                continue   # XXXX TODO blacklist instead?
            if files[child].blacklisted:
                blacklisted_by.add(child)
                
        return sorted(list(blacklisted_by))
    else:
        return []

def do_certify_file(basename, certifypath, check_references=False, filemap=None,
                    context=None):
    """Run un-trapped components of crds.certify and re-raise any exception
    as a CrdsError which will be displayed as a form error on the submission
    page.
    
    basename is the name of the file on the user's system,  hopefully with a
    sane extension.   certifypath is a fully qualified path,  but sometimes
    with a temporary filename which is total garbage.
    """
    try:
        certify.certify_files([certifypath], check_references=None,
            trap_exceptions=False, is_mapping = rmap.is_mapping(basename),
            context=context)
    except Exception, exc:
        raise CrdsError("Certifying " + srepr(basename) + ": " + str(exc))

    if check_references and rmap.is_mapping(basename):
        if filemap is None:
            filemap = models.get_fileblob_map(models.OBSERVATORY)
        ctx = rmap.fetch_mapping(certifypath)
        for ref in ctx.reference_names():
            assert ref in filemap, \
                "Reference " + srepr(ref) + " in " + srepr(basename) + " is not known to CRDS."

