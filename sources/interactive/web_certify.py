"""Functions supporting certification of files and presenting the cert output to the web.
Aside from output capture to strings,  handles weird web naming/path issues and temporaries...
while making the output look sane.
"""
import os.path
import re

from django.utils import html

from crds.core import rmap, log, config
from crds.core.exceptions import CrdsError
from crds import certify

from . import models
from .common import capture_output, srepr, html_colorize_log

def certify_file_list(upload_tuples, check_references=True, context=None, compare_old_reference=False,
                      push_status=lambda x: None):
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
    for (original_name, upload_path) in sorted(upload_tuples):
        # In order to capture output easily,  run as subprocess...
        push_status("Certifying '{}'".format(original_name))
        status, output = captured_certify(original_name, upload_path, 
            check_references=check_references, filemap=filemap, context=context, 
            compare_old_reference=compare_old_reference)
        certify_results[original_name] = status, html_colorize_log(output)
        if status == "Failed.":
            disposition = "bad files"
    return disposition, sorted(certify_results.items())


def captured_certify(original_name, uploaded_path, check_references=True, filemap=None, context=None,
                     compare_old_reference=False):
    """Run certify capturing and categorizing the output.
    
    Returns ("OK|"Warnings"|"Failed", certify_output) 
    """
    config.check_filename(original_name)
    output = _captured_certify(original_name, uploaded_path, context, compare_old_reference,
                               check_references, filemap)[1]
    if re.search(r"(CRDS\s+[\-\:]\s+ERROR)", output):
        status = "Failed."
    elif re.search(r"(CRDS\s+[\-\:]\s+WARNING)", output):
        status = "Warnings"
    else:
        status = "OK"
    return status, html.escape(output)

@capture_output
def _captured_certify(original_name, uploaded_path, context=None, compare_old_reference=False, check_references=False, 
                      filemap=None):
    """Run  crds.certify_files on `uploaded_path` and capture it's stdout/stderr."""
    certify.certify_file(uploaded_path, context=context, 
                         dump_provenance=True, check_references=False, 
                         original_name=original_name, compare_old_reference=compare_old_reference, 
                         observatory=models.OBSERVATORY, run_fitsverify=True)

    if check_references and rmap.is_mapping(original_name):
        if filemap is None:
            filemap = models.get_fileblob_map(models.OBSERVATORY)
        with log.error_on_exception("Failed checking mapping '%s'" % original_name):
            ctx = rmap.fetch_mapping(uploaded_path, ignore_checksum=True)
            # NOTE: There is some overlap between these checks and those crds.certify can do.
            # Checking for file existence this ways is faster than checking the file system.
            for filename in ctx.reference_names():
                if filename not in filemap or filemap[filename].state not in models.USEABLE_STATES:
                    log.error("File '%s' is not known to CRDS." % filename)
                else:
                    if filemap[filename].blacklisted:
                        log.error("File '%s' is blacklisted." % filename)
                    if filemap[filename].rejected:
                        log.warning("File '%s' is rejected." % filename)

def do_certify_file(original_name, certifypath, check_references=False, filemap=None, context=None):
    """Run un-trapped components of crds.certify and re-raise any exception
    as a CrdsError which will be displayed as a form error on the submission
    page.
    
    original_name is the name of the file on the user's system,  hopefully with a
    sane extension.   certifypath is a fully qualified path,  but sometimes
    with a temporary filename which is total garbage.
    """
    config.check_filename(original_name)
    old_trap = log.set_exception_trap(False)
    try:
        certify.certify_file(certifypath, check_references=None,
            original_name=original_name, context=context, observatory=models.OBSERVATORY,
            run_fitsverify=True)
    except Exception as exc:
        raise CrdsError("Certifying " + srepr(original_name) + ": " + str(exc))
    finally:
        log.set_exception_trap(old_trap)
        
    if check_references and rmap.is_mapping(original_name):
        if filemap is None:
            filemap = models.get_fileblob_map(models.OBSERVATORY)
        ctx = rmap.fetch_mapping(certifypath)
        for ref in ctx.reference_names():
            assert ref in filemap, \
                "Reference " + srepr(ref) + " in " + srepr(original_name) + " is not known to CRDS."

def get_blacklist_file_list(upload_tuples, all_files):
    """Return the mapping of blacklist status and blacklisted_by list for the
    given `uploaded_tuples` with respect to `all_files`.
    
    Returns { original_name :  (blacklist_status, blacklisted_by), ... }
    """
    blacklist_results = {}
    for (original_name, upload_path) in upload_tuples:
        config.check_filename(original_name)
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

def get_blacklists(original_name, certifypath, ignore_self=True, files=None):
    """Return a list of the files referenced by `original_name` which are
    blacklisted.
    """
    original_name = str(original_name)
    if rmap.is_mapping(original_name):
        blacklisted_by = set()
        try:
            mapping = rmap.fetch_mapping(certifypath, ignore_checksum=True)
        except Exception as exc:
            raise CrdsError("Error loading " + srepr(original_name) + " : " + str(exc))
        if files is None:
            files = models.get_fileblob_map(mapping.observatory)
        
        for child in mapping.mapping_names() + mapping.reference_names():
            config.check_filename(child)       
            if ignore_self and child == os.path.basename(certifypath): 
                continue
            if child not in files:   # Unknown file,  what to do?
                log.error("get_blacklists for", repr(original_name), "missing file", repr(child))
                continue   # XXXX TODO blacklist instead?
            if files[child].blacklisted:
                blacklisted_by.add(child)
                
        return sorted(list(blacklisted_by))
    else:
        return []

