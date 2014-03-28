"""This module accesses non-Django supporting databases using pyodbc,
unixODBC,  and FreeTDS,  to get dataset headers from the HST DADSOPS 
catalog.
"""
import pprint
import getpass
from collections import OrderedDict, defaultdict
import os.path

import pyodbc

from django.utils import html

from crds import rmap, log, utils, timestamp, config
from crds.server.interactive import models, common
from crds.server import config as sconfig

if models.OBSERVATORY == "hst":
    import crds.hst
    import crds.hst.parkeys as parkeys

log.set_verbose(False)

HERE = os.path.dirname(__file__) or "."
HEADER_TABLES = HERE + "/db_header_tables.dat"

# IPPPSSOOT   ---   dataset naming breakdown
#
# Denotes the instrument type:
# J - Advanced Camera for Surveys
# U - Wide Field / Planetary Camera 2
# V - High Speed Photometer
# W - Wide Field / Planetary Camera
# X - Faint Object Camera
# Y - Faint Object Spectrograph
# Z - Goddard High Resolution Spectrograph
# E - Reserved for engineering data
# F - Fine Guide Sensor (Astrometry)
# H-I,M - Reserved for additional instruments
# N - Near Infrared Camera Multi Object Spectrograph
# O - Space Telescope Imaging Spectrograph
# S - Reserved for engineering subset data
# T - Reserved for guide star position data
# PPP     Denotes the program ID, any combination of letters or numbers
# SS    Denotes the observation set ID, any combination of letters or numbers
# OO    Denotes the observation ID, any combination of letters or numbers
# T    Denotes the source of transmission:
# R - Real time (not tape recorded)
# T - Tape recorded
# M - Merged real time and tape recorded
# N - Retransmitted merged real time and tape recorded
# O - Retransmitted real time
# P - Retransmitted tape recorded
#

IPPPSSOOT_INSTR = {
    "J" : "acs",
    "U" : "wfpc2",
    "V" : "hsp",
    "W" : "wfpc",
    "X" : "foc",
    "Y" : "fos",
    "Z" : "hrs",
    "E" : "eng",
    "F" : "fgs",
    "I" : "wfc3",
    "N" : "nicmos",
    "O" : "stis",
    "L" : "cos",
}

INSTR_IPPPSSOOT = utils.invert_dict(IPPPSSOOT_INSTR)

# ---------------------------------------------------------------------------------------------

def explore_dadops_assocs(cat=None):
    """Count associated and unassociated exposures by instrument.  Experimental."""
    if cat is None:
        cat = get_catalog()

    stats = { "---" : ("assoc_ids", "assoc_hdrs", "unassoc_ids", "unassoc_hdrs", 
                       "assoc ids-headers", "unassoc ids-headers)") }

    for instr, instr_char in sorted(INSTR_IPPPSSOOT.items()):
        if instr not in models.INSTRUMENTS:
            log.verbose("Skipping", repr(instr))
            continue

        gen = get_instrument_gen(instr)
        assoc = gen._assoc_get_ids()
        unassoc = gen._unassoc_get_ids()
        assoc_hdrs = gen._assoc_get_headers()
        unassoc_hdrs = gen._unassoc_get_headers()

        stats[instr] = (len(assoc), len(assoc_hdrs), 
                        len(unassoc), len(unassoc_hdrs),
                        list(set(assoc)-set(assoc_hdrs.keys()))[:5],
                        list(set(unassoc)-set(unassoc_hdrs.keys()))[:5])

        print instr, stats[instr]

    return stats

def compare_headers_to_ids(instrument=None):
    """Compare the dataset header ids for `instrument` to the dataset_ids which
    are computed independently.   Experimental.
    """
    if instrument is None:
        comparison = [("instrument", "ids1", "ids2", "missing12", "missing21")]
        for instr in models.INSTRUMENTS:
            comparison.append(compare_headers_to_ids(instr))
        return comparison
    else:
        log.info("Comparing:", repr(instrument))
        ids1 = get_dataset_headers_by_instrument(instrument)
        gen = get_instrument_gen(instrument)
        ids2 = gen.get_dataset_ids()
        missing12 = set(ids1)-set(ids2)
        missing21 = set(ids2)-set(ids1)
        return (instrument, len(ids1), len(ids2), len(missing12), len(missing21))

# ---------------------------------------------------------------------------------------------

def dataset_to_instrument(dataset):
    """Convert `dataset` id to its corresponding instrument name."""
    instr = dataset[0].upper()
    try:
        return IPPPSSOOT_INSTR[instr]
    except KeyError:
        raise ValueError("Can't determine instrument for dataset " + repr(dataset))

class DB(object):
    """This is a basic raw interface to a database, exposing tables, columns, and SQL.
    It is also capable of converting any table into a list of dictionaries, one per row.
    """
    def __init__(self, dsn, user, password=None):
        self.dsn = dsn
        self.user = user
        if password is None:
            password = getpass.getpass("password: ")
        self.connection = pyodbc.connect("DSN=%s;Uid=%s;Pwd=%s" % (dsn, user, password))
        self.cursor = self.connection.cursor()

    def __repr__(self):
        return self.__class__.__name__ + "(%s, %s)" % (repr(self.dsn), repr(self.user))

    def execute(self, sql):
        log.verbose("Executing SQL:", repr(sql))
        return self.cursor.execute(sql)

    def lexecute(self, sql):
        gen = self.execute(sql)
        return sorted([tuple(t) for t in gen])

    def get_tables(self):
        return sorted(str(row.table_name) for row in self.cursor.tables())

    def get_columns(self, table):
        return [str(col.column_name) for col in self.cursor.columns(table=table)] # *** DO NOT SORT

    def make_dicts(self, table, col_list=None, ordered=False, where="", dataset=None, lowercase=True):
        if dataset is not None:
            all_cols = self.get_columns(table)
            for col in all_cols:
                if "data_set_name" in col:
                    dsname = col
                    break
            where += "where %s='%s'" % (dsname, dataset)

        if col_list is None:
            col_list = self.get_columns(table)
        col_names = ", ".join(col_list)
        if not col_names.strip():
            col_names = "*"

        for row in self.execute("select %s from %s %s" % (col_names, table, where)):
            items = zip(col_list, [str(x).lower() for x in row] if lowercase else row)
            kind = OrderedDict if ordered else dict
            yield kind(items)

# ---------------------------------------------------------------------------------------------

def get_password():
    """Return the password associated with this database,  retrieving it from a file if possible,
    otherwise prompting.
    """
    if not hasattr(get_password, "_password"):
        try: # crazy scheme works with "password" or "blah password" in password file.
            get_password._password = open(sconfig.CATALOG_DB_PFILE).read().split()[-1:][0]
        except:
            get_password._password = getpass.getpass("password: ")
    return get_password._password

def get_catalog(user=sconfig.CATALOG_DB_USER):
    """Cache and return a database connection to CATALOG."""
    if not hasattr(get_catalog, "_catalog"):
        get_catalog._catalog = DB(sconfig.CATALOG_DB_DSN, user, get_password())
    return get_catalog._catalog

def get_reffile_ops(user=sconfig.CATALOG_DB_USER):
    """Cache and return a database connection to REFFILE_OPS."""
    if not hasattr(get_reffile_ops, "_reffile_ops"):
        get_reffile_ops._reffile_ops = DB(sconfig.REFFILE_DB_DSN, user, get_password())
    return get_reffile_ops._reffile_ops

# ---------------------------------------------------------------------------------------------

# Functions related to scanning the tables looking for columns containing required keywords.
# These functions collectively generate db_header_tables.dat,  with some manual tweaking
# required so examine diffs carefully after any re-run of gen_header_tables.

def get_instrument_db_parkeys(instrument):
    """Return the union of the database versions of all parkeys for all
    filekinds of instrument.
    """
    dbkeys = set()
    for filekind in parkeys.get_filekinds(instrument):
        dbkeys = dbkeys.union(set(parkeys.get_db_parkeys(instrument, filekind)))
        dbkeys = dbkeys.union(set(parkeys.get_extra_keys(instrument, filekind)))
        switch = parkeys.get_reffile_switch(instrument, filekind)
        if switch.lower() != "none":
            dbkeys.add(switch)
    return sorted(dbkeys)

def required_keys(instr):
    """Get both the input parkeys and expected results keywords for
    all filekinds of `instr`ument`.
    """
    pars = get_instrument_db_parkeys(instr)
    pars.append("expstart" if instr != "stis" else "texpstrt")
    pars.append("data_set")
    # pars.append("program_id")
    # pars.append("obset_id")
    # pars.append("obsnum")
    pars.append("asn_id")
    pars.append("member_name") 
    pars.append("member_type")
    imap = rmap.get_cached_mapping(models.get_default_context(state="operational")).get_imap(instr)
    pars.extend(imap.selections.keys())
    return pars

def gen_header_tables(datfile=HEADER_TABLES):
    """gen_header_tables() generates the mapping: 
    
    { instrument : { best_refs_item : "table.column"  } }
    
    where best_refs_item is nominally the name of a best refs parameter or
    result or other relevant info,  assumed to be a substring of `column`.
    """
    table = {}
    for instr in crds.hst.INSTRUMENTS:
        table[instr] = clean_scan(instr)
    open(datfile, "w+").write(pprint.pformat(table) + "\n")
        
def clean_scan(instr):
    """clean_scan() sorts out the map produced by scan_tables(),  mapping each
    parameter of `instr` to a single "table.column" database location.
    Emits a warning for parameters which are not automatically mapped to the
    database.
    """
    columns, remainder = scan_tables(instr)
    if remainder:
        log.warning("For", repr(instr), "can't locate", sorted(list(remainder)))
    else:
        log.info("Collected", repr(instr), "ok")
    clean = {}
    for var in columns:
        tvar2 = columns[var]
        tvar = []
        for cand in tvar2:
            if "_old" not in cand:
                tvar.append(cand)

        for cand in tvar:
            if "best" in cand:
                tvar = [cand]
                break

        for cand in tvar:
            if "ref_data" in cand and "tv_ref_data" not in cand:
                tvar = [cand]
                break

        for cand in tvar:
            if "science" in cand and "tv_science" not in cand:
                tvar = [cand]
                break

        if len(tvar) == 1:
            clean[var] = tvar[0]
        elif len(tvar) == 2 and "best" in tvar[1] and "best" not in tvar[0]:
            clean[var] = tvar[1]
        else:
            clean[var] = tvar
            
    return clean

def scan_tables(instr):
    """scan_tables() automatically matches the required parameters for each
    instrument against the available instrument tables and columns in CATALOG,
    returning a map  { parameter : [ "table.column", ...] } finding plausible
    locations for each CRDS best refs parameter in the dataset catalog.
    """
    catalog = get_catalog()
    pars = required_keys(instr)
    columns = {}
    for table in catalog.get_tables():
        if instr not in table and "assoc_member" not in table:
            continue
        for par in pars:
            for col in catalog.get_columns(table):
                if par in col:
                    if par not in columns:
                        columns[par] = []
                    columns[par].append(str(table + "." + col))
    return columns, set(pars) - set(columns.keys())

# ---------------------------------------------------------------------------------------------

class CompoundId(str):
    """Store a compound "dataset" ID used to capture both member and association.
    Similar to a named tuple but possibly more JSON-friendly since ultimately it's a string.
    Assocations are groups of exposures each identified by it's member id.
    Not all exposures are "associated";  unassociated exposures have the same association and member id.
    """
    def __new__(cls, association, member):
        return super(CompoundId, cls).__new__(cls, association + ":" + member)

    def __init__(self, association, member):
        # super(CompoundId, self).__init__(association + ":" + member)
        self.association = association
        self.member = member
        
    def __repr__(self):
        return self.__class__.__name__ + "(association='{}', member='{}')".format(self.association, self.member)

    def __str__(self):
        return self.association + ":" + self.member

# ---------------------------------------------------------------------------------------------

class HeaderGenerator(object):
    def __init__(self, instrument, catalog_db, header_to_db_map):
        self.instrument = instrument.lower()
        self.catalog_db = catalog_db        
        self.h_to_db = header_to_db_map
        self.db_columns = self.h_to_db.values()
        self.db_tables = sorted(set(column.split(".")[0] 
                                    for column in self.db_columns))
        self.header_keys = tuple(key.upper() for key in self.h_to_db.keys())

    def _getter_sql(self, columns, tables, clauses=()):
        sql = "SELECT {} FROM {} ".format(
            ", ".join(columns), 
            ", ".join(tables))
        if clauses:
            sql += "WHERE " + " AND ".join(clauses)
        return sql

    def _get_headers(self, sql, header_keys):
        hdrs = {}
        for sql_row in self.catalog_db.execute(sql):
            hdr = dict(zip(header_keys, sql_row))
            hdr = self.condition_header(hdr)
            hdr = self.fix_hdr(hdr)
            hdrs[self.compound_id(hdr)] = hdr
        return hdrs

    def condition_header(self, hdr):
        return { key:utils.condition_value(hdr[key]) for key in hdr }

    def fix_hdr(self, hdr):
        return hdr
    
    def compound_id(self, hdr):
        """Given a dataset header,  construct and return a CompoundId .
        These have associated and unassociated forms.
        """
        if "ASN_ID" in hdr:
            return hdr["ASN_ID"] + ":" + hdr["MEMBER_NAME"]
        else:
            return hdr["DATA_SET"] + ":" + hdr["DATA_SET"]
        
class HstHeaderGenerator(HeaderGenerator):
    def __init__(self, *args, **keys):
        super(HstHeaderGenerator, self).__init__(*args, **keys)
        self.assoc_header_keys = tuple(self.header_keys)
        self.unassoc_header_keys = tuple(key
            for key in self.header_keys
            if  "assoc_member" not in self.h_to_db[key.lower()])
        self.table_prefix = { self.col_to_table(col):self.col_to_prefix(col) 
                              for col in self.db_columns }
        self.assoc_columns = tuple(self.db_columns)
        self.assoc_tables = tuple(self.db_tables)
        self.unassoc_columns = tuple(col for col in self.db_columns
                                     if "assoc_member" not in col)
        self.unassoc_tables = tuple(table for table in self.db_tables
                                    if table != "assoc_member")
        self.product_table = self.col_to_table(self.h_to_db["data_set"])
        self.exposure_tables = [table for table in self.db_tables
                                if self.level(table) == "exposure"]

    @property
    def instr_char(self):
        return INSTR_IPPPSSOOT[self.instrument]
    
    def level(self, table):
        if "assoc" in table:
            return "assoc"
        elif "ref_data" in table or "_science" in table:
            return "product"
        else:  # acs_a_data, acs_chip
            return "exposure"

    def col_to_table(self, col):
        """>>> col_to_table('wfpc2_ref_data.w2r_best_maskfile') 
        'wfpc2_ref_data'
        """
        return col.split(".")[0]

    def col_to_prefix(self, col):
        """>>> col_to_prefix('wfpc2_ref_data.w2r_best_maskfile') 
        'wfpc2_ref_data.w2r'
        """
        table, column = col.split(".")
        return table + "." + column[:3]

    def fix_hdr(self, hdr):
        hdr["INSTRUME"] = self.instrument.upper()
        hdr = dict(hdr)
        expstart = hdr.get("EXPSTART", hdr.get("TEXPSTRT"))
        try:
            hdr["DATE-OBS"], hdr["TIME-OBS"] = timestamp.format_date(expstart).split()
        except:
            log.warning("Bad database EXPSTART", expstart, hdr)
        return hdr 

    def get_headers(self, extra_clauses=()):
        headers = self._unassoc_get_headers(extra_clauses)
        if self.exposure_tables:
            headers.update(self._assoc_get_headers(extra_clauses))
        return headers

    def _assoc_get_headers(self, extra_clauses=()):
        assoc_sql = self._assoc_get_sql(extra_clauses)
        return self._get_headers(assoc_sql, self.assoc_header_keys)

    def _unassoc_get_headers(self, extra_clauses=()):
        unassoc_sql = self._unassoc_get_sql(extra_clauses)
        return self._get_headers(unassoc_sql, self.unassoc_header_keys)

    def _assoc_get_sql(self, extra_clauses=()):
        return self._getter_sql(self.assoc_columns, self.assoc_tables, 
                                tuple(self._assoc_join_clauses()) + 
                                tuple(extra_clauses))
    
    def _unassoc_get_sql(self, extra_clauses=()):
        return self._getter_sql(self.unassoc_columns, self.unassoc_tables,
                                tuple(self._unassoc_join_clauses()) + 
                                tuple(extra_clauses))

    def _assoc_join_clauses(self):
        """Return a list of table join constraints to AND together for 
        associated datasets based on the requested list of columns of
        the form [table.column, ...]
        """
        clauses = []
        if len(self.assoc_tables) < 2:
            return clauses
        for table in self.assoc_tables:
            if table == "assoc_member":
                continue
            tab_prefix = self.table_prefix[table]  # e.g. assoc_member.asm
            if self.level(table) == "product":
                clauses.append("assoc_member.asm_asn_id = {}_data_set_name".format(tab_prefix))
            else:
                for field in ["program_id", "obset_id", "obsnum"]:
                    clause = "{}_{} = {}_{}".format("assoc_member.asm", field, tab_prefix, field)
                    clauses.append(clause)
        return clauses

    def _unassoc_join_clauses(self):
        """Return a list of table join constraints to AND together for
        unassociated datasets based on the requested list of columns
        of the form [table.column, ...].  Unassociated datasets aren't
        mentioned in assoc_member at all.  The components of data_set_name
        should be joinable across all tables,

        Almost all tables supply data_set_name.  All tables seem to
        supply the pieces: program_id, obset_id, obsnum so just use
        those universally.  Bite tongue, cussing not allowed.
        """
        clauses = []
        if len(self.unassoc_tables) < 2:
            return clauses
        for table in self.unassoc_tables:
            if table == self.product_table:
                continue
            for field in ["program_id", "obset_id", "obsnum"]:
                clause = "{}_{} = {}_{}".format(self.table_prefix[self.product_table], field, 
                                                self.table_prefix[table], field)
                clauses.append(clause)
        return clauses

    def get_expstart_clause(self, datasets_since):
        return self.h_to_db.get("expstart", self.h_to_db.get("texpstrt")) + " >= '" + datasets_since + "'"
    
    def get_dataset_ids(self):
        return sorted(self._assoc_get_ids() + self._unassoc_get_ids())

    def _assoc_get_ids(self):
        return self._make_ids(self._assoc_get_id_sql())

    def _unassoc_get_ids(self):
        return self._make_ids(self._unassoc_get_id_sql())

    def _make_ids(self, sql):
        return list(set([row[0] + ":" + row[1] for row in self.catalog_db.execute(sql)]))

    def _assoc_get_id_sql(self):
        id_columns = ["assoc_member.asm_asn_id", "assoc_member.asm_member_name"]
        return self._getter_sql(id_columns, self.assoc_tables, 
                                tuple(self._assoc_join_clauses()))

    def _unassoc_get_id_sql(self):
        id_columns = [self.h_to_db["data_set"], self.h_to_db["data_set"]]
        return self._getter_sql(id_columns, self.unassoc_tables, 
                                tuple(self._unassoc_join_clauses()))

# ---------------------------------------------------------------------------------------------

HEADER_MAP = None
HEADER_GENERATORS = {}

def init_db():
    """Create HeaderGenerator's for each instrument and set up a global map."""
    global HEADER_MAP, HEADER_TABLES, HEADER_GENERATORS
    if HEADER_MAP is None:
        with log.error_on_exception("Failed loading", repr(HEADER_TABLES)):
            HEADER_MAP = utils.evalfile(HEADER_TABLES)
            with log.error_on_exception("Failed getting catalog connection"):
                connection = get_catalog()
                with log.error_on_exception("Failed setting up header generators"):
                    HEADER_GENERATORS = {}
                    for instr in HEADER_MAP:
                        HEADER_GENERATORS[instr] = HstHeaderGenerator(instr, connection, HEADER_MAP[instr])
                        
def get_instrument_gen(instrument):
    """Return the header generator for `instrument`."""
    init_db()
    return HEADER_GENERATORS[instrument.lower()]

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
    
# ---------------------------------------------------------------------------------------------------------
def get_dataset_headers_by_instrument(instrument, observatory="hst", datasets_since=None):
    """Get the header for a particular dataset,  nominally in a context where
    one only cares about a small list of specific datasets.
    """
    if datasets_since is None:
        datasets_since = "1900-01-01 00:00:00"
    init_db()
    _check_instrument(instrument)
    _check_observatory(observatory)
    _check_date(datasets_since)
    try:
        igen = HEADER_GENERATORS[instrument]
        extra_clauses = [ igen.get_expstart_clause(datasets_since) ] if datasets_since else []
        return igen.get_headers(extra_clauses)
    except Exception, exc:
        raise RuntimeError("Error accessing catalog for instrument" + repr(instrument) + ":" + str(exc))

# ---------------------------------------------------------------------------------------------------------
MAX_IDS = 5000

"""
Here's the strategy for ID specification as-of now, it may evolve:

Fully specified ID's are of the form <product>:<member>.   <product>'s are defined
by data_set_name (and/or program_id, obset_id, obsnum) in the ref_data table for an instrument.

Since there is no "destructive" overlap between <product> and <member>,  it's also
possible to ask for <product> or <member> in a partially specified ID with no colon.
(for unassociated exposures,  <product> == <member>,  but the resulting header is the same
for both. that's "non-destructive" overlap.)

Asking for <product> will return <product>:<member> for all associated members.

Asking for <member> will return <product>:<member> for the associated product.

In the case of unassociated exposures,  <member> == <product>, so <member>:<member> is returned.

The way the query works is to constrain the "data_set" column to be in [<products>, ...].

data_set always corresponds to data_set_name in the product level ref_data table.

data_set will join either to exposure level tables for unassociated exposures,  or to the
association table asm_asn_id for associated exposures.   associated exposures further join
to exposure tables via asm_member_name which takes the place of data_set_name.

In both cases,  the bulk of the query constraint comes from the table join.  A tertiary
aspect of constraint is to ensure that only requested product exposures are returned.

Since for unassociated exposures, <product> == <member>,  it's enough to constrain on <product>
to get all matching headers.

A minor bug is that this approach returns complete association sets even when a specific
associated exposure is requested.

"""

def get_dataset_headers_by_id(dataset_ids, observatory="hst"):
    """Based on a list of `dataset_ids`,  return the corresponding DADSOPS bestrefs matching parameters."""

    for did in dataset_ids:
        _check_dataset_id(did)
    _check_observatory(observatory)

    assert len(dataset_ids) <= MAX_IDS, \
           "Too many ids.   More than {} datasets specified.".format(MAX_IDS)

    init_db()
    
    datasets = sorted([did.upper() for did in set(dataset_ids)])
    products = sorted(list(set([ did.split(":")[0] for did in datasets ])))

    by_instrument = defaultdict(list)
    for product in products:
        instrument = dataset_to_instrument(product)
        by_instrument[instrument].append(product)

    all_headers = {}
    for instrument, products in by_instrument.items():
        try:
            igen = HEADER_GENERATORS[instrument]
            comma_product_ids = ", ".join(["'{}'".format(did) for did in products])
            product_clause = "{} in ({})".format(igen.h_to_db["data_set"], comma_product_ids)
            headers = igen.get_headers(extra_clauses=[product_clause])
        except Exception, exc:
            raise RuntimeError("Error accessing catalog for instrument " + repr(instrument) + ":" + str(exc))
        all_headers.update(headers)

    products = [ cid.split(":")[0] for cid in all_headers ]
    exposures = [ cid.split(":")[1] for cid in all_headers ]
    combined = all_headers.keys()
    found_ids  = sorted(set(products + exposures + combined))

    missing = [ did for did in datasets if did not in found_ids ]

    all_headers.update( { did : "NOT FOUND" for did in missing } )

    return all_headers

# ---------------------------------------------------------------------------------------------------------
def get_dataset_ids(instrument, observatory="hst"):
    """Return a list of the known dataset ids for `instrument`."""
    init_db()
    _check_instrument(instrument)
    _check_observatory(observatory)
    igen = HEADER_GENERATORS[instrument]
    return igen.get_dataset_ids()

# ---------------------------------------------------------------------------------------------------------
def get_reference_info(instrument, reference):
    """Return file info for a CDBS reference file `reference` belonging to `instrument`."""
    _check_instrument(instrument)
    _check_filename(reference)
    if instrument == "nicmos": 
        instrument = "nic"
    elif instrument == "wfii":
        instrument = "wfpc2"
    refops = get_reffile_ops()
    gen = refops.make_dicts(instrument.lower() + "_file", where="WHERE file_name='{}'".format(reference.lower()))
    return gen.next()

