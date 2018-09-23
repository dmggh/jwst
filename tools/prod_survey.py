"""This script is used in the analysis of DADSOPS associations and type patterns.
"""
from collections import defaultdict
from pprint import pprint as pp

from crds_server.interactive import database as db
from crds import python23

# from crds import log
# log.set_verbose()

def get_associations(where=""):
    cat = db.get_catalog()
    assocs = cat.lexecute("select asm_asn_id, asm_member_name, asm_member_type from assoc_member {}".format(where))
    return assocs

def collapse_by_asn(assocs):
    collapsed = defaultdict(list)
    for member in sorted(assocs):
        collapsed[member[0]].append(member[2])
    return collapsed

def collapse_by_types(collapsed):
    by_types = defaultdict(list)
    for asn_id, types in list(collapsed.items()):
        by_types[tuple(types)].append(asn_id)
    return by_types

def organize(by_types):
    organized = []
    for types, ids in list(by_types.items()):
        organized.append((len(ids), ids[0], types))
    return list(reversed(sorted(organized)))

def classify_assoc_patterns():
    assocs = get_associations()
    collapsed = collapse_by_asn(assocs)
    by_types = collapse_by_types(collapsed)
    organized = organize(by_types)
    return organized

def get_unique_assoc_types():
    cat = db.get_catalog()
    types = cat.lexecute("select distinct asm_member_type from assoc_member")
    return [t[0] for t in types]

def get_missing(sample):
    headers = db.get_synthetic_dataset_headers_by_id([sample])
    assocs = get_associations(where="WHERE asm_asn_id = '{}'".format(sample))
    missing = []
    for (asn, member, member_type) in assocs:
        compound = asn + ":" + member
        if compound.upper() not in headers:
            missing.append(member)
    member_types = { member:member_type for (asn, member, member_type) in assocs } 
    found_tups = sorted([ (member_types[member_id(compound)], member_id(compound))
                          for compound in headers 
                          if not isinstance(headers[compound], python23.string_types) ])
    missing_tups = sorted([ (member_types[member], member) for member in missing ])
    return missing_tups, found_tups, assocs

def member_id(compound):
    return compound.split(":")[1]

def scan_missing(classified):
    missing_count = 0
    missing_types = set()
    busted_count = 0
    busted_types = set()
    busted_instruments = set()
    for count, sample, pattern in classified:
        print("-"*100)
        print("**scanning**", count, sample, pattern)
        missing, found, assocs = get_missing(sample)
        if missing:
            print("**found**   ", count, sample, len(found), len(assocs), found, pattern)
            print("**missing** ", count, sample, len(missing), len(assocs), missing, pattern)
            if not len(found):
                print("**bust**", count, sample, pattern)
                busted_count += count
                for (type, member) in missing:
                    busted_types.add(typ)
                busted_instruments.add(db.dataset_to_instrument(sample))
            # print count, sample, assocs
            missing_count += 1
            for (typ, member) in missing:
                missing_types.add(typ)
    return missing_count, sorted(list(missing_types)), busted_count, sorted(list(busted_types))

def main():
    print("=" * 100)
    types = get_unique_assoc_types()
    print("There are", len(types), "unique assoc member types:\n", types)
    classified = classify_assoc_patterns()
    print()
    print()
    print("=" * 100)
    print("There are", len(classified), "different assoc type patterns.")
    print("=" * 100)
    print("%-20s | %10s | %s" % ("assocs-using-pattern",  "sample-id", "unique-type-pattern"))
    print("=" * 100)
    for tup in classified:
        print("%-20s | %10s | %s" % tup)
    print()
    print()
    print("=" * 100)
    missing_count, missing_types, busted_count, busted_types = scan_missing(classified)
    print("=" * 100)
    print("There are", missing_count, "patterns with unrepresented exposures.")
    print("These", len(missing_types), "had missing members:\n", missing_types)
    print("=" * 100)
    print("There are", busted_count, "patterns with unrepresented exposures.")
    print("These", len(busted_types), "had missing members:\n", busted_types)

if __name__ == "__main__":
    main()

