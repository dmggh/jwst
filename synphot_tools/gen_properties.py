"""This module is used to test HST reffile file properties identification
code:  instrument and filetype.   With six supported instruments and a 
seventh pseudo-instrument,  and a twenty five year history,  file naming
and type idenfication conventions are complicated.
"""
import os, sys

from crds import log, utils, rmap

def gen_naming_truth(observatory, refs):
    """Scan all reference files and generate a simple text map with
    with one reference file per line of the form:

    <instrument> <filekind> <filename>

    This is used to create regression information so that changes to 
    the complex file properties determination code aren't broken for
    any of the existing types during maintenance.
    """
    files = 0
    # refs = rmap.list_references("*", observatory, full_path=True)
    truth_file = open(f"naming_{observatory}.txt","w+")
    prop_func = utils.get_object(
        "crds." + observatory + ".locate." + "ref_properties_from_header")
    header_func = lambda x: prop_func(x)[2:4]
    # header_func = lambda x: utils.get_file_properties(observatory, x)
    for filepath in refs:
        with log.error_on_exception(
                "Error determining file properties for", repr(filepath)):
            instrument, filekind = header_func(filepath)
            truth = instrument, filekind, os.path.basename(filepath)
            log.info(truth)
            truth_file.write(" ".join(truth) + "\n")
            if files and files % 20 == 0:
                truth_file.flush()
    truth_file.close()

    # Generate out sorted version as well to group by instrument regardless of name
    with open(f"naming_{observatory}.sorted.txt","w+") as truth_sorted:
        with open(f"naming_{observatory}.txt") as truth_unsorted:
            lines = truth_unsorted.read().splitlines()
        truth_sorted.write("\n".join(sorted(lines)) + "\n")

if __name__ == "__main__":
    gen_naming_truth(sys.argv[1], sys.argv[2:])

