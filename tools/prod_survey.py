"""This script is used in the analysis of DADSOPS associations and type patterns.
"""

from collections import defaultdict
from pprint import pprint as pp

from crds.server.interactive import database as db


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
    for asn_id, types in collapsed.items():
        by_types[tuple(types)].append(asn_id)
    return by_types

def organize(by_types):
    organized = []
    for types, ids in by_types.items():
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
    headers = db.get_dataset_headers_by_id([sample])
    assocs = get_associations(where="WHERE asm_asn_id = '{}'".format(sample))
    missing = []
    for (asn, member, member_type) in assocs:
        if asn != member:
            compound = asn + ":" + member
            if compound.upper() not in headers:
                missing.append(member)
    member_types = { member:member_type for (asn, member, member_type) in assocs } 
    found = sorted([ (member_types[member_id(compound)], member_id(compound))
                     for compound in headers 
                     if not isinstance(headers[compound], basestring) ])
    missing = sorted([ (member_types[member], member) for member in missing ])
    return missing, found, assocs

def member_id(compound):
    return compound.split(":")[1]

def scan_missing(classified):
    missing_count = 0
    missing_types = set()
    for count, sample, pattern in classified:
        print "-"*100
        print "**scanning**", count, sample, pattern
        missing, found, assocs = get_missing(sample)
        if missing:
            print "**found**   ", count, sample, len(found), len(assocs)-1, found, pattern
            print "**missing** ", count, sample, len(missing), len(assocs)-1, missing, pattern
            # print count, sample, assocs
            missing_count += 1
            for (typ, member) in missing:
                missing_types.add(typ)
    return missing_count, sorted(list(missing_types))

def main():
    print "=" * 100
    types = get_unique_assoc_types()
    print "There are", len(types), "unique assoc member types:\n", types
    classified = classify_assoc_patterns()
    print
    print
    print "=" * 100
    print "There are", len(classified), "different assoc type patterns."
    print "=" * 100
    print "%-20s | %10s | %s" % ("assocs-using-pattern",  "sample-id", "unique-type-pattern")
    print "=" * 100
    for tup in classified:
        print "%-20s | %10s | %s" % tup
    print
    print
    print "=" * 100
    missing_count, missing_types = scan_missing(classified)
    print "=" * 100
    print "There are", missing_count, "patterns with unrepresented exposures."
    print "These types had missing members:\n", missing_types

if __name__ == "__main__":
    main()

