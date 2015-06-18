"""This module defines functions for producing a fusion between a context
json or dict representation and the catalog entries associated with the
corresponding files.
"""
import re

from crds.server.interactive import models, html
from crds import config, rmap

#
# catalog fields are an item list mapping FileBlob attributes to web page column labels
#
#
# CATALOG_FIELDS = (
#     ("activation_date_str", "Activation Date"),
# )
#

@models.crds_cached
def get_rmap_web_parameters(mapping, catalog_fields):
    """Return the datatables dictionary corresponding to `mapping`.
    """
    header, rows = get_fused_rmap_parameters( mapping, catalog_fields)
    web_header, web_rows  = webify_parameters(header, rows)
    return web_header, web_rows

def webify_parameters(header, rows):
    """Modify stock header and rows to include a file link and diff checkbox / button.
    Also simplify JWST parameter names by removing META. prefix.
    """
    # header already ends with "filename",  extend with diff button
    fixed_header = fix_meta_parameters(header)
    web_header = fixed_header + (html.input("", type='submit', id='diff_button', value='diff'),)
    web_rows = []
    # extend each row,  replacing filename with link,  extending with diff checkbox
    for row in rows:
        filename = row[-1]
        web_row = row[:-1] + ("<a href='/browse/{0}'>{1}</a>".format(filename, filename),                      
                              "<input type='checkbox' value='{0}' />".format(filename),)
        web_rows.append(web_row)
    return web_header, web_rows

def fix_meta_parameters(parameters):
    """Web-hack for JWST,  ditch the wordy META. prefix on every parameter just
    for the context display.
    """
    if isinstance(parameters, basestring):
        return parameters.replace("META.","")
    else:
        return tuple([fix_meta_parameters(par) for par in parameters])

# =======================================================================================================    

def get_fused_rmap_parameters(mapping, catalog_fields=models.FileBlob.fusion_items):
    """Return the datatables dictionary corresponding to `rmap_name`."""
    from crds.server.interactive.views import is_rmap

    mapping_name, rmap_dict = get_mapping_dict(mapping)
    assert is_rmap(mapping_name), "mapping must be an .rmap"
    header = rmap_dict["parameters"]
    # Header ends with filename,  insert catalog field names prior to filename title in tuple.
    header = header[:-1] + tuple(field[1].upper() for field in catalog_fields) + (header[-1],)
    # For each file row, insert catalog field values prior to filename value in tuple
    fileblobs = models.get_fileblob_map()
    fileblobs["N/A"] = fileblobs["n/a"] = fileblobs["TEMP_N/A"] = fileblobs["temp_n/a"] = None
    rows = []
    for row in rmap_dict["selections"]:
        filename = row[-1]
        extended_row = (row[:-1] + 
                        tuple(getattr(fileblobs[filename], field[0], "--") for field in catalog_fields) + 
                        (filename,))
        rows.append(extended_row)
    return header, rows

def get_mapping_dict(mapping):
    """Given mapping spec `mapping`,  return the dictionary representation."""
    if re.match(config.complete_re(r"operational|edit"), mapping):
        mapping = models.get_default_context(state=mapping)
    config.is_mapping(mapping)
    loaded_mapping = rmap.get_cached_mapping(mapping)
    return mapping, loaded_mapping.todict()

