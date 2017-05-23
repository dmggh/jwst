"""test_associations: Test of general Association functionality."""
from __future__ import absolute_import

import os
import pytest
import re

from .helpers import full_pool_rules

from ..main import Main

# Temporarily skip if running under Travis
# pytestmark = pytest.mark.skipif(
#     "TRAVIS" in os.environ and os.environ["TRAVIS"] == "true",
#     reason='Temporarily disable due to performance issues'
# )


def test_script(full_pool_rules):
    pool, rules, pool_fname = full_pool_rules

    generated = Main([pool_fname, '--dry-run'])
    asns = generated.associations
    assert len(asns) == 35
    assert len(generated.orphaned) == 2
    found_rules = set(
        asn['asn_rule']
        for asn in asns
    )
    assert 'candidate_Asn_Image' in found_rules
    assert 'candidate_Asn_WFSCMB' in found_rules


def test_asn_candidates(full_pool_rules):
    pool, rules, pool_fname = full_pool_rules

    generated = Main([pool_fname, '--dry-run', '-i', 'o001'])
    assert len(generated.associations) == 3
    generated = Main([pool_fname, '--dry-run', '-i', 'o001', 'o002'])
    assert len(generated.associations) == 5


def test_toomanyoptions(full_pool_rules):
    pool, rules, pool_fname = full_pool_rules

    with pytest.raises(SystemExit):
        generated = Main([
            pool_fname,
            '--dry-run',
            '--discover',
            '--all-candidates',
            '-i', 'o001',
        ])
    with pytest.raises(SystemExit):
        generated = Main([
            pool_fname,
            '--dry-run',
            '--discover',
            '--all-candidates',
        ])
    with pytest.raises(SystemExit):
        generated = Main([
            pool_fname,
            '--dry-run',
            '--discover',
            '-i', 'o001',
        ])
    with pytest.raises(SystemExit):
        generated = Main([
            pool_fname,
            '--dry-run',
            '--all-candidates',
            '-i', 'o001',
        ])


@pytest.mark.skip(reason='Need to further investigate')
def test_discovered(full_pool_rules):
    pool, rules, pool_fname = full_pool_rules

    full = Main([pool_fname, '--dry-run'])
    candidates = Main([pool_fname, '--dry-run', '--all-candidates'])
    discovered = Main([pool_fname, '--dry-run', '--discover'])
    assert len(full.associations) == len(candidates.associations) + len(discovered.associations)


def test_version_id(full_pool_rules):
    pool, rules, pool_fname = full_pool_rules

    generated = Main([pool_fname, '--dry-run', '-i', 'o001', '--version-id'])
    regex = re.compile('\d{3}t\d{6}')
    for asn in generated.associations:
        assert regex.search(asn.asn_name)

    version_id = 'mytestid'
    generated = Main([pool_fname, '--dry-run', '-i', 'o001', '--version-id', version_id])
    for asn in generated.associations:
        assert version_id in asn.asn_name

def test_pool_as_parameter(full_pool_rules):
    pool, rules, pool_fname = full_pool_rules

    full = Main([pool_fname, '--dry-run'])
    full_as_param = Main(['--dry-run'], pool=pool)
    assert len(full.associations) == len(full_as_param.associations)