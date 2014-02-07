"""Handles web presentation of CRDS file differences."""

import os.path
import re

from crds import rmap, pysh, CrdsError, log, config

from . import common

GEIS_HEADER_RE = r"\w+(\.r\dh)"

def mass_differences(pair_or_quad_tuples, connector=" --> ", push_status=lambda x: None):
    """Get the differences info for each tuple in `pair_or_quad_tuples`,  where
    a pair is a tuple of two known file basenames,  and a quad adds full paths
    corresponding to the basenames,  which are probably file temporaries not in
    the official file tree. Used for file submission and multiple generated files.
    """
    # key must be a string to json encode as a repeatable result.
    diffs = { tup[0] +  connector + "<span class='blue'>" + tup[1] + "</span>" : 
                difference_core(*tup, push_status=push_status) for tup in pair_or_quad_tuples }
    return sorted(diffs.items())

# Although not spelled that way in the code,  AFAIK,  file1 == old_file and file2 == new_file.
# Each diff describes some change in the evolution from old --> new.
def difference_core(file1_orig, file2_orig, file1_path=None, file2_path=None, push_status=lambda x: None):
    """Compute the rendering dictionary for the differences include file."""

    assert os.path.splitext(file1_orig)[-1] == os.path.splitext(file2_orig)[-1], \
        "Differenced files should be of the same type and have the same extension."

    if file1_path is None:
        file1_path = rmap.locate_mapping(file1_orig)
    if file2_path is None:
        file2_path = rmap.locate_mapping(file2_orig)

    push_status("Differencing '{}' vs. '{}'".format(file1_orig, file2_orig))
    
    def extension(filename): 
        """Return the file extension of `filename`."""
        return os.path.splitext(filename)[1]
    
    logical_errors = logical_diffs = header_diffs = map_text_diff_items = None
    if rmap.is_mapping(file1_orig) and rmap.is_mapping(file2_orig) and \
          extension(file1_orig) == extension(file2_orig):
        unfiltered, logical_errors = mapping_logical_diffs(file1_orig, file2_orig, file1_path, file2_path)
        # filter to same type because table display requires homogeneous columns
        filtered = filter_same_type(file1_path, unfiltered)
        # logical diffs are stored as json,  make json-ify-able items
        logical_diffs = [ diff.flat.items() for diff in filtered if "header" not in diff[-1] and "different" not in diff[-1] ]
        header_diffs = [ diff for diff in filtered if "header" in diff[-1] or "different" in diff[-1] ]
        header_diffs = [ diff.flat.items() for diff in header_diffs if not boring_diff(diff) ]
        # map_text_diffs = mapping_text_diffs(logical_diffs)
        # Compute root files separately since they may have upload paths.
        map_text_diffs = {}
        difference = textual_diff(file1_orig, file2_orig, file1_path, file2_path)
        map_text_diffs[str((file1_orig, file2_orig))] = difference
        map_text_diff_items = sorted(map_text_diffs.items())
    else:
        file1_path = config.check_path(file1_path)
        file2_path = config.check_path(flie2_path)
        diff_lines = pysh.out_err("python -m crds.diff ${file1_path} ${file2_path}").splitlines()   # secured
        difference = '\n'.join(diff_lines)
    if not difference.strip():
        difference = "no differences"
    return {
       "logical_errors" : logical_errors,
       "logical_diffs" : logical_diffs,
       "header_diffs" : header_diffs,
       "map_text_diff_items" : map_text_diff_items,
       "difference" : difference,
       "file1" : file1_orig,
       "file2" : file2_orig,
    }
    
def boring_diff(diff):
    """Return True IFF a logical diff is more boring than normal,  i.e. routine formal header changes."""
    return ("replaced 'derived_from'" in diff[-1]) or ("replaced 'name'" in diff[-1]) or ("replaced 'sha1sum'" in diff[-1]) 

def textual_diff(file1_orig, file2_orig, file1_path=None, file2_path=None):
    """Return the output of the context diff of two files."""
    if file1_path is None:
        file1_path = rmap.locate_mapping(file1_orig)
    if file2_path is None:
        file2_path = rmap.locate_mapping(file2_orig)
    file1_path = config.check_path(file1_path)
    file2_path = config.check_path(file2_path)
    diff_lines = pysh.lines("diff -b -u -FUseAfter ${file1_path} ${file2_path}")  # secured
    result = []
    for line in diff_lines:
        line = line.replace(file1_path, file1_orig)
        line = line.replace(file2_path, file2_orig)
        result.append(line)
    return ''.join(result)

def mapping_logical_diffs(file1_orig, file2_orig, file1, file2):
    """Return the logical differences between two mapping files."""
    try:
        map1 = rmap.fetch_mapping(file1, ignore_checksum=True)
        map2 = rmap.fetch_mapping(file2, ignore_checksum=True)
        # Get logical difference tuples
        ldiffs = map1.difference(map2, include_header_diffs=True)
        result = ldiffs, []
    except Exception, exc:
        file1, file2 = map(os.path.basename, [file1, file2])
        exc = str(exc).replace(file1, file1_orig).replace(file2, file2_orig)
        result = [], ["ERROR: " + exc ]
    # log.info("mapping_logical_diffs:", log.PP(result))
    return result

def mapping_text_diffs(logical_diffs):
    """Return a mapping of file pairs to the textual differences between them
    for all of the mappings mentioned in `logical_diffs`.   Skips over the first
    logical difference tuple since that corresponds to the top level files,  
    which might have been uploaded and hence the file paths aren't known here.
    """
    diff_map = {}
    for ldiff in logical_diffs:
        for tup in ldiff:
            if isinstance(tup, tuple) and len(tup) == 2 and \
                tup[0].endswith("map") and tup[1].endswith("map"):
                file1_orig, file2_orig = tup
                file1_path = rmap.locate_mapping(file1_orig)
                file2_path = rmap.locate_mapping(file2_orig)
                key = str((os.path.basename(file1_orig), os.path.basename(file2_orig)))
                if  key not in diff_map:
                    try:
                        diffs = textual_diff(file1_orig, file2_orig, file1_path, file2_path)
                    except Exception, exc:
                        diffs = "diffs failed: " + str(exc)
                    diff_map[key] = diffs
    return diff_map

def filter_same_type(file1_path, logical_diffs):
    """Filter `logical_diffs` down to only those with the same type as `file_path`.  This
    bolts on the behavior of a non-recursive or less-recursive difference.
    """
    filtered = set()
    ext = os.path.splitext(file1_path)[1]
    for diff in logical_diffs:
        for tup in diff:
            if tup and len(tup) == 2 and tup[0].endswith("map") and \
                os.path.splitext(tup[0])[1] != ext:
                break
        else:
            filtered.add(diff)
    return sorted(list(filtered))

def format_fitsdiffs(lines, file1, file2, file1_orig, file2_orig):
    """Add some colorization to output `lines` from fitsdiff, replacing
    `file1` and `file2` with their basenames.
    """
    for i in range(len(lines)):
        line = clean_path(lines[i], file1, file1_orig)
        line = clean_path(line, file2, file2_orig)
        if "Primary HDU" in line or re.search(r"Extension HDU \d+", line):
            line = "<h3>" + line + "</h3>"
        line = re.sub(r"([Kk]eyword)\s*([A-Za-z0-9_]*)",
                      r"\1 <span class='green'>\2</span>", line)
        lines[i] = line
    return lines

def clean_path(line, path, file_orig):
    """Replace occurrences of `path` in `line` with a greyed version of
    the `path`s basename.
    """
    base = "<span class='grey'>" + os.path.basename(file_orig) + "</span>"
    return line.replace(path, base)

