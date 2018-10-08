"""This module is used to render some portion of the contents of a reference
file as HTML for the server reference file details page.
"""
import os
import os.path
import re
import tempfile

# ---------------------------------------------------------------------------------

from django.utils.html import format_html, format_html_join

from astropy.io import fits as pyfits

# ---------------------------------------------------------------------------------

import crds
from crds.core import config, log, pysh
from crds import data_file

from .common import srepr, capture_output

from . import models

# ---------------------------------------------------------------------------------

def browsify_file(filename, browsed_file):
    """Return the HTML rendering of `filename` for use in the file details Content panel"""
    filetype = config.filetype(filename) # mapping, fits, json, yaml, finf, text, unknown
    try:
        browsifier = globals()["browsify_" + filetype]
        file_contents = browsifier(filename, browsed_file)
    except Exception as exc:
        log.error("browsify_file failed: ", str(exc))
        file_contents = "<pre class='error'>Content display for '{}' not available</pre>".format(
            os.path.basename(filename))
    return file_contents

def browsify_fits(filename, browsed_file):
    """Format a CRDS reference file for HTML display.   Return HTML lines."""
    output = browsify_header(filename, browsed_file)
    output += browsify_finfo(filename, browsed_file)
    return output

def browsify_header(filename, browsed_file):
    """Fetch the minimum matching header of `filename` under the current operational
    context and format it as HTML.
    """
    ref_blob = models.FileBlob.load(os.path.basename(browsed_file))
    default_context = models.get_default_context(ref_blob.observatory, "edit")
    mapping = crds.get_symbolic_mapping(default_context)
    header = {}
    with log.error_on_exception("Failed getting minimum header for", repr(browsed_file)):
        header = mapping.get_minimum_header(browsed_file)
    header2 = {}
    with log.error_on_exception("Failed getting extra keys for", repr(browsed_file)):
        header2 = data_file.get_unconditioned_header(browsed_file, needed_keys=("APERTURE","USEAFTER"))
    if not header:
        with log.error_on_exception("Fallback to FITS header union failed."):
            header = data_file.get_fits_header_union(browsed_file)
    if header:
        header.update(header2)
        output  = "<b>Header Parameters</b>\n"
        output += "<br/>\n"
        output += "<br/>\n"
        output += "<table border='1'>\n"
        for key, value in sorted(header.items()):
            if value != "UNDEFINED":
                output += format_html("<tr><td class='tdlabel'>{0}</td><td>{1}</td></tr>\n", key, value)
        output += "</table>\n"
    else:
        output = format_html("<p class='error'>File header unavailable for '{0}'</p>", browsed_file)
    output += "<br/>\n"
    return output

def browsify_finfo(filename, browsed_file):
    """Fetch the equivalent of FITS info output and format as HTML."""
    output = ""
    try:
        fits_info = finfo(browsed_file)[1] + "\n"
    except Exception as exc:
        output += format_html("<p class='error'>FITS info unavailable: '{0}'</p>", exc)
    else:
        output += "<p><b>FITS Info</b></p>\n"
        output += "<br/>\n"
        output += "<div class='simple_white'>\n"
        output += "<pre class='simple_white'>\n"
        lines = fits_info.split("\n")
        if lines[0].lower().startswith("filename"):
            lines = lines[1:]
        output += format_html_join("\n", "{0}", ((line,) for line in lines))
        output += "</pre>\n"
        output += "</div>\n"
        output += "<br/>\n"
    return output

def browsify_asdf(filename, browsed_file):
    """Format an ASDF file as HTML."""
    info = browsify_header(filename, browsed_file)
    with log.error_on_exception("Can't extract ASDF tree from", srepr(browsed_file)):
        tree = get_asdf_tree(browsed_file)
        info += "<b>ASDF Tree</b>\n"
        info += "<br/>+\n"
        info += "<div class='simple_white'>\n"
        info += "<pre>\n" + tree + "\n</pre>\n"
        info += "</div>\n"
    return info

def get_asdf_tree(filepath):
    """Read the YAML tree out of an ASDF file and return it."""
    assert re.match(config.FILE_PATH_RE, filepath),  "Bad file path extracting ASDF tree contents."
    with tempfile.NamedTemporaryFile() as temp:
        return pysh.out_err("asdftool to_yaml {} --output {} --resolve-references; cat {}".format(filepath, temp.name, temp.name))
    # with asdf.AsdfFile.open(filepath) as handle:
    #     return str(handle.tree)

@capture_output
def finfo(filename):
    """Capture the output from the pyfits info() function."""
    pyfits.info(filename)

def browsify_text(filename, browsed_file):
    """Format a CRDS text file as colorized HTML."""
    try:
        contents = open(browsed_file).read()
    except IOError:
        return format_html("<h3 class='error'>File <span class='grey'>{0}<span> not found</h3>", filename)
    return format_html("<pre class='program'>\n{0}</pre>", contents)

def browsify_mapping(filename, browsed_file):
    """Format a CRDS mapping file for HTML display.  Return HTML string."""
    return browsify_text(filename, browsed_file)

def browsify_yaml(filename, browsed_file):
    """Format a CRDS YAML reference file for HTML display.   Return HTML string."""
    return browsify_text(filename, browsed_file)

def browsify_json(filename, browsed_file):
    """Format a CRDS JSON reference file for HTML display.   Return HTML string."""
    return browsify_text(filename, browsed_file)

def browsify_geis(filename, browsed_file):
    browsed_header = browsed_file[:-1] + "h"
    return browsify_text(filename, browsed_header)
