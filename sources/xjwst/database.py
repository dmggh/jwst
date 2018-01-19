"""This module accesses fetches best reference matching parameters from a JWST
archive web service.
"""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
# from builtins import str
import pprint
import getpass
from collections import OrderedDict, defaultdict, namedtuple
import os.path
import json
import re

import pyodbc

from django.utils import html

import crds
from crds.core import log, utils, timestamp, config, rmap
from crds import bestrefs
from crds import jwst

from crds.server.interactive import models, common
from crds.server.interactive import views as iviews
from crds.server import config as sconfig

from crds.server.xjwst import parameter_interface

# =========================================================================================================

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
    _safe_assert(iviews.is_pmap(context), "Invalid context " + repr(context))
    return context.lower()

# ---------------------------------------------------------------------------------------------------------

class InvalidDatasetIdError(RuntimeError):
    """The format of a dataset id is bad."""

# ---------------------------------------------------------------------------------------------------------

MOCK_PARAMETERS = None

def deferred_load_mock_parameters():
    """Defer the time consuming loading of any mock parameters dictionary to run time
    if they're actually used.
    """
    global MOCK_PARAMETERS
    if sconfig.CRDS_MOCK_ARCHIVE_PARAMETERS:
        if MOCK_PARAMETERS is None:
            path = os.path.join(HERE, sconfig.CRDS_MOCK_ARCHIVE_PARAMETERS)
            log.info("Loading mock archive parameters from", repr(path))
            MOCK_PARAMETERS = bestrefs.load_bestrefs_headers(path)
    else:
        MOCK_PARAMETERS = None
    return MOCK_PARAMETERS

def mock_params(instrument, date):
    params = deferred_load_mock_parameters()
    if params is not None:
        if instrument.lower() == "system":
            return []
        params = filter_by_instrument(instrument, params)
        params = filter_by_date(date, params)
    else:
        params = {}
    for param in params.values():
        if isinstance(param, dict):
            param["PARAMS_SOURCE"] = sconfig.CRDS_MOCK_ARCHIVE_PARAMETERS
    return params

def filter_by_instrument(instrument, params):
    return { dataset_id : header for (dataset_id, header) in list(params.items())
             if get_instrument(header).upper() == instrument.upper() } 

def get_instrument(header):
    return header["META.INSTRUMENT.NAME"]

def filter_by_date(datasets_since, params):
    return { dataset_id : header for (dataset_id, header) in list(params.items())
             if get_date(header) >= datasets_since }

def get_date(header):
    return header["META.OBSERVATION.DATE"] + " " + header["META.OBSERVATION.TIME"]

# ---------------------------------------------------------------------------------------------------------

def get_dataset_ids(instrument, datasets_since=None):
    """Return a list of the known dataset ids for `instrument`."""
    if datasets_since is None:
        datasets_since = "1900-01-01 00:00:00"
    _check_instrument(instrument)
    _check_date(datasets_since)
    if instrument.lower() == "system":
        return []
    params = mock_params(instrument, datasets_since)
    if params:
        return list(params.keys())
    else:
        return parameter_interface.get_dataset_ids(instrument, datasets_since)

# ---------------------------------------------------------------------------------------------------------

DETECTOR_TO_INSTRUMENT = {   # XXXX non-invertible
    "GUIDER" : "FGS", # 1,2

    "NIS" : "NIRISS",
    "NIRISS" : "NIRISS",

    "NRCA" : "NIRCAM",  # 1,2,3,4,LONG
    "NRCB" : "NIRCAM",  # 1,2,3,4,LONG

    "NRS" : "NIRSPEC",  # 1,2

    "MIRI" : "MIRI", # LONG,SHORT,IMAGE
}

def get_dataset_headers_by_id(context, dataset_ids):
    """Based on a list of `dataset_ids`,  return { dataset_id: { param_name : param_value, ... }, ...} where
    the set of param_names is determined by `context` with respect to the instruments 
    implicitly defined in `dataset_ids`.
    """
    _check_context(context)

    for did in dataset_ids:
        _check_dataset_id(did)

    headers = dict()

    normalized_ids = get_normalized_ids(dataset_ids)

    params = mock_params_by_ids(context, normalized_ids)
    if params:
        return params

    ids_by_instrument = defaultdict(list)
    for dataset in normalized_ids:
        for detector, instrument in list(DETECTOR_TO_INSTRUMENT.items()):
            if detector.upper() in dataset.upper():
                ids_by_instrument[instrument].append(str(dataset))
                break
        else:
            log.warning("No instrument name found for dataset:", repr(dataset))
            headers[dataset.upper()] = "NOT FOUND No instrument name found for dataset"

    pmap =  crds.get_pickled_mapping(context)   # reviewed
    
    matching_params = { 
        instr : list((set(pmap.get_imap(instr).get_required_parkeys())-set(["REFTYPE"]))|set(["META.INSTRUMENT.NAME"])) 
        for instr in ids_by_instrument 
        }
    
    for instr, dids in list(ids_by_instrument.items()):
        instr_headers = parameter_interface.get_dataset_headers_by_id(context, dids, matching_params[instr])
        headers.update(instr_headers)

    return headers

def mock_params_by_ids(context, dataset_ids):
    """Return fake parameter sets for each ID in `dataset_ids`.
    Where normally `context` may affect available parameters,  in this
    case it is ignored.
    """
    params = deferred_load_mock_parameters()
    if params:
        selected_params = {}
        for dataset_id in dataset_ids:
            try:
                selected_params[dataset_id] = dict(params[dataset_id])
            except:
                selected_params[dataset_id] = "NOT FOUND no parameter set for dataset."
        return selected_params
    else:
        return {}

# ----------------------------------------------------------------------------------------------------------
# e.g.   jw90001001001_02101_00001_nis  -->  jw90001001001_02101_00001.nis
# Hack fileset names into dotted format as a convenience

JWST_FILESET_RE_STR = r"[A-Za-z0-9]{13}_[A-Za-z0-9]{5}_[A-Za-z0-9]{5}_[A-Za-z0-9]{3,15}"
JWST_FILESET_RE = re.compile(config.complete_re(JWST_FILESET_RE_STR))

def get_normalized_ids(dataset_ids):
    normalized_ids = []
    for dataset in dataset_ids:
        dataset = dataset.upper()
        if JWST_FILESET_RE.match(dataset):
            parts = dataset.split("_")
            dataset = "_".join(parts[:-1]) + "." + parts[-1]
        if ":" not in dataset:
            dataset = dataset + ":" + dataset
        normalized_ids.append(dataset)
    return normalized_ids

# ---------------------------------------------------------------------------------------------------------

def get_synthetic_dataset_headers_by_id(context, dataset_ids):
    """Leverage the association table to provide headers for member ids which don't
    successfully join through all an instrument's tables.  Use headers for ids which do 
    join through all tables as surrogates for ids which don't,  based on member type patterns.

    Return { dataset_id : { matching_parameters}, err_id : "NOT FOUND ..."}

    NOTE: function included as place holder for same functionality actually used in HST not
    currently needed for JWST.
    """
    return get_dataset_headers_by_id(context, dataset_ids)

