"""This script is used in the analysis of DADSOPS associations and type patterns.
"""

from collections import defaultdict
from pprint import pprint as pp

from crds.server.interactive import database as db


def get_associations():
    cat = db.get_catalog()
    assocs = cat.lexecute("select asm_asn_id, asm_member_name, asm_member_type from assoc_member")
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

if __name__ == "__main__":
    main()

