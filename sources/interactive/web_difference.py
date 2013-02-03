import os.path
import re

from crds import rmap, pysh, CrdsError

GEIS_HEADER_RE = r"\w+(\.r\dh)"

def mass_differences(pair_or_quad_tuples, connector=" --> "):
    """Get the differences info for each tuple in `pair_or_quad_tuples`,  where
    a pair is a tuple of two known file basenames,  and a quad adds full paths
    corresponding to the basenames,  which are probably file temporaries not in
    the official file tree. Used for file submission and multiple generated files.
    """
    # key must be a string to json encode as a repeatable result.
    diffs = { tup[0] +  connector + "<span class='blue'>" + tup[1] + "</span>" : 
                difference_core(*tup) for tup in pair_or_quad_tuples }
    return sorted(diffs.items())

def difference_core(file1_orig, file2_orig, file1_path=None, file2_path=None):
    """Compute the rendering dictionary for the differences include file."""

    if file1_path is None:
        file1_path = rmap.locate_mapping(file1_orig)
    if file2_path is None:
        file2_path = rmap.locate_mapping(file2_orig)
    
    def extension(filename): 
        """Return the file extension of `filename`."""
        return os.path.splitext(filename)[1]
    
    logical_diffs = map_text_diff_items = None
    if rmap.is_mapping(file1_orig) and rmap.is_mapping(file2_orig) and \
        extension(file1_orig) == extension(file2_orig):
        logical_diffs = mapping_logical_diffs(file1_path, file2_path, file1_orig, file2_orig)
        map_text_diffs = mapping_text_diffs(logical_diffs)
        # Compute root files separately since they may have upload paths.
        difference = textual_diff(file1_orig, file2_orig, file1_path, file2_path)
        map_text_diffs[str((file1_orig, file2_orig))] = difference
        map_text_diff_items = sorted(map_text_diffs.items())
        logical_diffs = [[ str(tup) for tup in diff] for diff in logical_diffs]
    elif file1_orig.endswith(".fits") and file2_orig.endswith(".fits"):
        diff_lines = pysh.lines("fitsdiff ${file1_path} ${file2_path}")
        diff_lines = format_fitsdiffs(diff_lines, file1_path, file2_path,
            file1_orig, file2_orig)
        difference = ''.join(diff_lines)
    elif re.match(GEIS_HEADER_RE, file1_orig) and re.match(GEIS_HEADER_RE, file2_orig) and \
        extension(file1_orig) == extension(file2_orig):
        difference = textual_diff(file1_orig, file2_orig, file1_path, file2_path)
    else:
        raise CrdsError("Files should be either CRDS mappings "
                        "of the same type or .fits files")        
    if not difference.strip():
        difference = "no differences"
    return {
       "logical_diffs" : logical_diffs,
       "map_text_diff_items" : map_text_diff_items,
       "difference" : difference,
       "file1" : file1_orig,
       "file2" : file2_orig,
    }

def textual_diff(file1_orig, file2_orig, file1_path=None, file2_path=None):
    """Return the output of the context diff of two files."""
    if file1_path is None:
        file1_path = rmap.locate_mapping(file1_orig)
    if file2_path is None:
        file2_path = rmap.locate_mapping(file2_orig)
    diff_lines = pysh.lines("diff -b -u -FUseAfter ${file1_path} ${file2_path}")
    result = []
    for line in diff_lines:
        line = line.replace(file1_path, file1_orig)
        line = line.replace(file2_path, file2_orig)
        result.append(line)
    return ''.join(result)

def mapping_logical_diffs(file1, file2, file1_orig, file2_orig):
    """Return the logical differences between two mapping files."""
    try:
        map1 = rmap.fetch_mapping(file1, ignore_checksum=True)
        map2 = rmap.fetch_mapping(file2, ignore_checksum=True)
        # Get logical difference tuples
        ldiffs = map1.difference(map2)
        # Substitute the name of the original file for temp file.
#        for ldiff in ldiffs:
#            ldiff = replace_ldiff_file(ldiff, file1, file1_orig)
#            ldiff = replace_ldiff_file(ldiff, file2, file2_orig)
        return ldiffs
    except Exception, exc:
        return [("Mapping logical difference failed: " + str(exc),)]

def replace_ldiff_file(ldiff, file_temp, file_orig):
    """Replaces name of web temporary file in ldiff tuple with original upload 
    name.
    """ 
    if not len(ldiff):
        return ldiff
    tup = ldiff[0]
    if len(tup) == 2:
        if tup[0] == file_temp:
            tup = (file_orig, tup[1])
        if tup[1] == file_temp:
            tup = (tup[0], file_orig)
    return (tup,) + replace_ldiff_file(ldiff[1:], file_temp, file_orig)

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
                if (file1_orig, file2_orig) not in diff_map:
                    try:
                        diffs = textual_diff(
                            file1_orig, file2_orig, file1_path, file2_path)
                    except Exception, exc:
                        diffs = "diffs failed: " + str(exc)
                    diff_map[str((file1_orig, file2_orig))] = diffs
    return diff_map

def format_fitsdiffs(lines, file1, file2, file1_orig, file2_orig):
    """Add some colorization to output `lines` from fitsdiff, replacing
    `file1` and `file2` with their basenames.
    """
    for i in range(len(lines)):
        line = clean_path(lines[i], file1, file1_orig)
        line = clean_path(line, file2, file2_orig)
        if "Primary HDU" in line or re.search("Extension HDU \d+", line):
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

