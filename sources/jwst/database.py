"""This module accesses fetches best reference matching parameters from a JWST
archive web service.
"""
import pprint
import getpass
from collections import OrderedDict, defaultdict, namedtuple
import os.path

import pyodbc

from django.utils import html

import crds
from crds import rmap, log, utils, timestamp, config, jwst
from crds.server.interactive import models, common
from crds.server.interactive import views as iviews
from crds.server import config as sconfig

from crds.server.jwst import parameter_interface

HERE = os.path.dirname(__file__) or "."

# =========================================================================================================

# ---------------------------------------------------------------------------------------------------------
# From here down,  functions are untrusted API calls to access database services.
# These functions must explicitly screen all input parameters to guard against SQL injection attacks.
# ---------------------------------------------------------------------------------------------------------

def _safe_assert(condition, msg):
    """Assert `condition`,  using an HTML-escaped version of `msg` as a guard against XSS."""
    safe_msg = html.conditional_escape(msg)
    assert condition, safe_msg

def _check_dataset_id(did):
    """Raise an exception if `did` is not a valid CRDS dataset id."""
    _safe_assert(common.DATASET_ID_RE.match(did),  "Invalid dataset id " + repr(did))

def _check_observatory(obs):
    """Raise an exception if `obs` is not a valid CRDS observatory name."""
    _safe_assert(obs in models.OBSERVATORIES, "Invalid observatory " + repr(obs))

def _check_instrument(instr):
    """Raise an exception if `instr` is not a valid instrument for this site."""
    _safe_assert(instr in models.INSTRUMENTS, "Invalid instrument " + repr(instr))

def _check_date(date):
    """Raise an exception if `date` is not a valid CRDS context date specification."""
    _safe_assert(timestamp.DATETIME_RE.match(date), "Invalid date " + repr(date))
    
def _check_filename(filename):
    """Raise an exception if `filename` is not a valid CRDS filename."""
    _safe_assert(config.FILE_RE.match(filename), "Invalid file name " + repr(filename))

def _check_context(context):
    """Raise an exception if `context` is not a valid CRDS .pmap"""
    _safe_assert(iviews.is_pmap, "Invalid context " + repr(context))
    return context.lower()

# ---------------------------------------------------------------------------------------------------------

def get_dataset_headers_by_id(context, dataset_ids):
    """Based on a list of `dataset_ids`,  return { dataset_id: { param_name : param_value, ... }, ...} where
    the set of param_names is determined by `context` with respect to the instruments 
    implicitly defined in `dataset_ids`.
    """
    _check_context(context)

    for did in dataset_ids:
        _check_dataset_id(did)

    ids_by_instrument = defaultdict(list)
    for dataset in dataset_ids:
        for instrument in jwst.INSTRUMENTS:
            if instrument.upper() in dataset.upper():
                ids_by_instrument[instrument].append(dataset)
                break
        else:
            log.warning("No instrument name found for dataset:", repr(dataset))

    pmap =  rmap.get_cached_mapping(context)
    
    matching_parnames = { 
        instr : pmap.get_imap(instr).get_required_parkeys() for instr in ids_by_instrument 
        }
    
    headers = dict()
    for insr, dataset_ds in ids_by_instrument.items():
        instr_headers = parameter_interface.get_dataset_headers_by_id(dataset_ids, matching_params[instr])
        headers.update(instr_headers)

    return headers

def assoc_assoc_id(id):
    """Return True IFF the ID is of the form <assoc>:<assoc>."""
    parts = id.split(":")
    return len(parts) == 2 and parts[0] == parts[1] and parts[0].endswith("0")

class InvalidDatasetIdError(RuntimeError):
    """The format of a dataset id is bad."""

# ---------------------------------------------------------------------------------------------------------

def get_synthetic_dataset_headers_by_id(context, dataset_ids):
    """Leverage the association table to provide headers for member ids which don't
    successfully join through all an instrument's tables.  Use headers for ids which do 
    join through all tables as surrogates for ids which don't,  based on member type patterns.

    Return { dataset_id : { matching_parameters}, err_id : "NOT FOUND ..."}
    """
    id_map = get_synthetic_id_map([did.upper() for did in dataset_ids])
    source_ids = [did[0] for did in sorted(list(set(id_map.values())))]
    source_headers = get_dataset_headers_by_id(context, source_ids)
    headers = { did : source_headers[src_id] for (did, (src_id, typ, ctype)) in id_map.items() if src_id in source_headers }
    return headers

def partition_dataset_ids(dataset_ids):
    """Split an incoming list of dataset_ids into association and member ids.

    Ids can be of form:    
           <assoc>0
           <member>[^0]
           <assoc>0:<member>[^0]
           
    Returns ([<assoc>0, ...],  [<member>, ...])
    """
    dataset_ids = [did.upper() for did in dataset_ids]
    assocs, members = set(), set()
    for did in dataset_ids:
        if ":" in did:
            assoc, member = did.split(":")
            assocs.add(assoc)
            members.add(member)
        else:
            if did.endswith("0"):
                assocs.add(did)
            else:
                members.add(did)
    return list(assocs), list(members)

def compound_id(assoc, member):
    """Constructs a CRDS compound id from an association ID and a member ID."""
    return assoc.upper() + ":" + member.upper()

# ---------------------------------------------------------------------------------------------------------

def get_dataset_ids(instrument, datasets_since=None):
    """Return a list of the known dataset ids for `instrument`."""
    if datasets_since is None:
        datasets_since = "1900-01-01 00:00:00"
    _check_instrument(instrument)
    _check_date(datasets_since)
    return parameter_interface.get_dataset_ids(instrument, datasets_since)
