"""Helpers for tests."""
from backports.tempfile import TemporaryDirectory
from collections import namedtuple
from contextlib import contextmanager
from glob import glob
import os
import pytest
import re

from astropy.table import (Table, vstack)

from .. import (AssociationRegistry, AssociationPool, generate)
from ..association import is_iterable
from ..lib.counter import Counter


# Define how to setup initial conditions with pools.
class PoolParams(
        namedtuple(
            'PoolParams',
            [
                'path',
                'n_asns',
                'n_orphaned',
                'candidates',
                'kwargs'
            ]
        )
):
    def __new__(cls, path='',
                n_asns=0,
                n_orphaned=0,
                candidates=None,
                kwargs=None):
        if not kwargs:
            kwargs = {}
        if candidates is None:
            candidates = []
        return super(PoolParams, cls).__new__(
            cls,
            path,
            n_asns,
            n_orphaned,
            candidates,
            kwargs
        )


# Basic Pool/Rule test class
class BasePoolRule(object):

    # Define the pools and testing parameters related to them.
    # Each entry is a tuple starting with the path of the pool.
    pools = []

    # Define the rules that SHOULD be present.
    # Each entry is the class name of the rule.
    valid_rules = []

    def setup(self):
        """You set me up...."""

    def tearDown(self):
        """You tear me down..."""

    def test_rules_exist(self):
        rules = AssociationRegistry()
        assert len(rules) >= len(self.valid_rules)
        rule_names = get_rule_names(rules)
        for rule in self.valid_rules:
            assert rule in rule_names

    def test_run_generate(self):
        rules = AssociationRegistry()
        for ppars in self.pools:
            pool = combine_pools(ppars.path, **ppars.kwargs)
            (asns, orphaned) = generate(pool, rules)
            assert len(asns) == ppars.n_asns
            assert len(orphaned) == ppars.n_orphaned
            for asn, candidates in zip(asns, ppars.candidates):
                assert set(asn.candidates) == set(candidates)


@pytest.fixture(scope='session')
def full_pool_rules(request):
    pool_fname = t_path('data/mega_pool.csv')
    pool = AssociationPool.read(pool_fname)
    rules = AssociationRegistry()

    return (pool, rules, pool_fname)


def make_megapool():
    """Combine the individual test pools into one

    Notes
    -----
    This is meant to be run in the source tree in
    the folder the test pools reside in. The package
    does need to have been installed.
    `python -c 'import jwst.associations.tests.helpers as helpers; helpers.make_megapool()'`
    """
    pool_files = glob('pool_*.csv')
    pool_files.sort()
    pool = combine_pools(pool_files)
    pool.write(
        'mega_pool.csv',
        format='ascii',
        delimiter='|',
        overwrite=True
    )


# Basic utilities.
def check_in_list(element, alist):
    assert element in alist


def check_not_in_list(element, alist):
    assert element not in alist


def check_equal(left, right):
    assert left == right


def not_none(value):
    assert value is not None


def t_path(partial_path):
    """Construction the full path for test files"""
    test_dir = os.path.dirname(__file__)
    return os.path.join(test_dir, partial_path)


def combine_pools(pools, **pool_kwargs):
    """Combine pools into a single pool

    Parameters
    ----------
    pools: str, astropy.table.Table, [str|Table, ...]
        The pools to combine. Either a singleton is
        passed or and iterable can be passed.
        The entries themselves can be either a file path
        or an astropy.table.Table-like object.

    pool_kwargs: dict
        Other keywoard arguments to pass to AssociationPool.read

    Returns
    -------
    AssociationPool|astropy.table.Table
        The combined pool
    """
    if not is_iterable(pools):
        pools = [pools]
    just_pools = []
    for pool in pools:
        if not isinstance(pool, Table):
            pool = AssociationPool.read(pool, **pool_kwargs)
        just_pools.append(pool)
    if len(just_pools) > 1:
        mega_pool = vstack(just_pools, metadata_conflicts='silent')
    else:
        mega_pool = just_pools[0].copy(copy_data=True)

    # Replace OBS_NUM and ASN_CANDIDATE_ID with actual numbers, if
    # necessary
    expnum = Counter(start=0)
    obsnum = Counter(start=0)
    acid = Counter(start=999)
    local_env = locals()
    global_env = globals()
    for row in mega_pool:
        mega_pool[row.index] = [
            parse_value(v, global_env=global_env, local_env=local_env)
            for v in row
        ]

    return mega_pool


def parse_value(v, global_env=None, local_env=None):
    """Evaluate if indicated"""
    if global_env is None:
        global_env = globals()
    if local_env is None:
        local_env = locals()

    result = v
    try:
        m = re.match('@!(.+)', v)
    except TypeError:
        pass
    else:
        if m:
            result = eval(m.group(1), global_env, local_env)
    return result


def fmt_cand(candidate_list):
    """Format the candidate field

    Parameters
    ----------
    candidate_list: iterator
        An iterator with each element a 2-tuple of:
            cid: int
                Candidate ID
            ctype: str
                Candidate type

    Returns
    -------
    candidate_list_field: str
        A string of the list of candidates, with any evaluation
        performed.
    """
    evaled_list = []
    for cid, ctype in candidate_list:
        if isinstance(cid, int):
            if ctype == 'OBSERVATION' and cid < 1000:
                cid_format = 'o{:0>3d}'
            elif ctype in ['MOSAIC'] and cid >= 1000 and cid < 3000:
                cid_format = 'c{:0>4d}'
            else:
                cid_format = 'r{:0>4d}'
        else:
            cid_format = cid

        cid_str = cid_format.format(cid)
        evaled_list.append((cid_str, ctype))

    return str(evaled_list)


def fmt_fname(expnum):
    """Format the filename"""
    return 'jw_{:0>5d}_uncal.fits'.format(next(expnum))


def generate_params(request):
    """Simple param reflection for pytest.fixtures"""
    return request.param


def func_fixture(f, **kwargs):
    """Create a true decorator for pytest.fixture

    Parameters
    ----------
    f: func
        The function.

    kwargs: dict
        Keyword arguments to pass to pytest.fixture
    """
    @pytest.fixture(**kwargs)
    def duped(request, *duped_args, **duped_kwargs):
        return f(request, *duped_args, **duped_kwargs)
    return duped


@contextmanager
def mkstemp_pool_file(pools, **pool_kwargs):
    """Make an actual pool file"""
    pool = combine_pools(pools, **pool_kwargs)
    with TemporaryDirectory() as path:
        pool_path = os.path.join(path, 'pool')
        pool.write(
            pool_path,
            format='ascii',
            delimiter='|',
        )
        yield pool_path


def generate_pool_paths(request):
    """Fixture to create temporary files for pools"""
    pool_file = t_path(request.param)
    with mkstemp_pool_file(pool_file) as pool_path:
        yield pool_path


def get_rule_names(rules):
    """Return rules names found in a registry

    Parameters
    ----------
    rules: AssociationRegistry
        The registry to look through

    Returns
    -------
    rule_names: list
        The list of rule names
    """
    return [
        rule._asn_rule()
        for rule_name, rule in rules.items()
    ]