"""This module accesses non-Django supporting databases using pyodbc,
unixODBC,  and FreeTDS,  to get dataset headers from the HST DADSOPS 
catalog.
"""
import pprint
import getpass
from collections import OrderedDict, defaultdict, namedtuple
import os.path

import pyodbc

from django.utils import html

import crds
from crds.core import rmap, log, utils, timestamp, config
from crds_server.interactive import models, common
from crds_server import config as sconfig

from crds import hst
from crds.hst import locate, reftypes

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

FitsToDadsTuple = namedtuple("FitsToDadsTuple", ["observatory", "instrument", "fits", "field", "table", "empty1", "empty2"])
FITS_TO_DADS = dict()

def load_FITS_to_DADS():
    """Load the mapping from FITS keywords to DADS database fields for the HST catalog."""
    global FITS_TO_DADS
    for line in open(os.path.join(HERE, "dads_keywords.bdf")).read().splitlines():
        tup = FitsToDadsTuple(*[name.lower() for name in line.split("|")]) # Somebody wrote a module for this.
        FITS_TO_DADS[(tup.instrument, tup.fits)] = tup.table + "." + tup.field

# ---------------------------------------------------------------------------------------------

def explore_dadops_assocs(cat=None):
    """Count associated and unassociated exposures by instrument.  Experimental."""
    if cat is None:
        cat = get_catalog()

    stats = { "---" : ("assoc_ids", "assoc_hdrs", "unassoc_ids", "unassoc_hdrs", 
                       "assoc ids-headers", "unassoc ids-headers)") }

    for instr in sorted(INSTR_IPPPSSOOT):
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

        print(instr, stats[instr])

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
        raise crds.CrdsError("Can't determine instrument for dataset " + repr(dataset))

class DB(object):
    """This is a basic raw interface to a database, exposing tables, columns, and SQL.
    It is also capable of converting any table into a list of dictionaries, one per row.
    """
    def __init__(self, dsn, user, database=None):
        self.dsn = dsn
        self.user = user
        self.database = database
        os.system("kinit crds -k -t " + sconfig.CATALOG_DB_KEYTAB)
        self.connection = pyodbc.connect("DSN=%s; DATABASE=%s" % (dsn, database), autocommit=True)
        self.cursor = self.connection.cursor()

    def __repr__(self):
        return self.__class__.__name__ + repr((self.dsn, self.user, self.database))

    def execute(self, sql):
        log.verbose("Executing SQL:", repr(sql))
        return self.cursor.execute(sql)

    def lexecute(self, sql):
        gen = self.execute(sql)
        return sorted([tuple(t) for t in gen])

    @utils.cached
    def get_tables(self):
        return sorted(str(row.table_name) for row in self.cursor.tables())

    @utils.cached
    def get_columns(self, table):
        return [str(col.column_name) for col in self.cursor.columns(table=table)] # *** DO NOT SORT

    def get_instrument_tables(self, instrument):
        return [ table for table in self.get_tables() if table.startswith(instrument)]

    def get_instrument_columns(self, instrument):
        return sorted([table + "." + col 
                      for table in self.get_instrument_tables(instrument)
                      for col in self.get_columns(table)])

    def make_dicts(self, table, col_list=None, ordered=False, where="", dataset=None):
        if dataset is not None:
            all_cols = self.get_columns(table)
            for col in all_cols:
                if "data_set_name" in col:
                    dsname = col
                    break
            where += " (WHERE %s='%s')" % (dsname, dataset)

        if col_list is None:
            col_list = self.get_columns(table)
        col_names = ", ".join(col_list)
        if not col_names.strip():
            col_names = "*"

        for row in self.execute("SELECT %s FROM %s %s" % (col_names, table, where)):
            undefined_and_lowercase = [str(x).lower() if x is not None else "UNDEFINED" for x in row]
            items = list(zip(col_list, undefined_and_lowercase))  # OK no list
            kind = OrderedDict if ordered else dict
            yield kind(items)

# ---------------------------------------------------------------------------------------------

def get_catalog():
    """Cache and return a database connection to CATALOG."""
    if not hasattr(get_catalog, "_catalog"):
        get_catalog._catalog = DB(
            sconfig.CATALOG_DB_DSN, sconfig.CATALOG_DB_USER, sconfig.CATALOG_DB_NAME)
    return get_catalog._catalog

# ---------------------------------------------------------------------------------------------

# Functions related to scanning the tables looking for columns containing required keywords.
# These functions collectively generate db_header_tables.dat,  with some manual tweaking
# required so examine diffs carefully after any re-run of gen_header_tables.

def get_instrument_db_parkeys(instrument):
    """Return the union of the database versions of all parkeys for all
    filekinds of instrument.
    """
    dbkeys = set()
    for filekind in reftypes.get_filekinds(instrument):
        dbkeys = dbkeys.union(set(reftypes.get_item(instrument, filekind, "parkey")))
        dbkeys = dbkeys.union(set(reftypes.get_item(instrument, filekind, "extra_keys")))
        switch = reftypes.get_item(instrument, filekind, "reffile_switch")
        if switch.lower() != "none":
            dbkeys.add(switch)
    log.info("Parkeys for", repr(instrument), "=", sorted(list(dbkeys)))
    rowkeys = crds.hst.locate.get_row_keys_by_instrument(instrument)
    log.info("Rowkeys for", repr(instrument), "=", rowkeys)
    dbkeys = dbkeys.union(set(rowkeys))
    return sorted([key.lower() for key in dbkeys])

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
    pars.append("asm_asn_id")
    pars.append("asm_member_name") 
    pars.append("asm_member_type")
    imap = crds.get_pickled_mapping(models.get_default_context(models.OBSERVATORY, "operational")).get_imap(instr)  # reviewed
    pars.extend(list(imap.selections.keys()))
    return pars

def gen_header_tables(datfile=HEADER_TABLES):
    """gen_header_tables() generates the mapping: 
    
    { instrument : { best_refs_item : "table.column"  } }
    
    where best_refs_item is nominally the name of a best refs parameter or
    result or other relevant info,  assumed to be a substring of `column`.
    """
    log.info("All DADSOPS tables:", get_catalog().get_tables())
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
    load_FITS_to_DADS()
    columns, remainder = scan_tables(instr)
    if remainder:
        log.warning("For", repr(instr), "can't locate", sorted(list(remainder)))
        log.info("Columns for", repr(instr),"are", log.PP(get_catalog().get_instrument_columns(instr)))
    else:
        log.info("Collected", repr(instr), "ok")
    return columns

def scan_tables(instr):
    """scan_tables() automatically matches the required parameters for each
    instrument against the available instrument tables and columns in CATALOG,
    returning a map  { parameter : [ "table.column", ...] } finding plausible
    locations for each CRDS best refs parameter in the dataset catalog.
    """
    log.reset()
    catalog = get_catalog()
    pars = required_keys(instr)
    columns = dict()
    tables = catalog.get_instrument_tables(instr) + ["assoc_member"]
    log.info("Scanning for", repr(instr), "tables =", tables)
    remainder = []
    for par in pars:
        columns[par] = []
        for table in tables:
            if instr not in table and table != "assoc_member":
                continue
            try:
                field = FITS_TO_DADS[(instr, par)]
                if field not in columns[par]:
                    columns[par].append(field)
                log.info("FITS_TO_DADS found for", (instr, par))
                break
            except KeyError:
                for col in catalog.get_columns(table):
                    if par in col:
                        field = str(table + "." + col)
                        if field not in columns[par]:
                            columns[par].append(field)
                            log.info("Turbo hog wild, SCORE for", repr(par), "=", field)
        if not columns[par]:
            log.error("FITS_TO_DADS + 'turbo hog wild' both BUST for", (instr, par))
            remainder.append(par)
        elif len(columns[par]) == 1: 
            columns[par] = columns[par][0]
    log.standard_status()
    return columns, sorted(remainder)

# ---------------------------------------------------------------------------------------------

class HeaderGenerator(utils.Struct):
    def __init__(self, instrument, catalog_db, header_to_db_map):
        self.instrument = instrument.lower()
        self.catalog_db = catalog_db
        self.h_to_db = header_to_db_map
        self.db_columns = list(self.h_to_db.values())
        self.db_tables = sorted(set(column.split(".")[0] 
                                    for column in self.db_columns))
        self.header_keys = tuple(key.upper() for key in list(self.h_to_db.keys()))

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
            hdr = dict(list(zip(header_keys, sql_row)))
            hdr = self.condition_header(hdr)
            hdr = self.fix_hdr(hdr)
            hdrs[self.compound_id(hdr)] = hdr
        return hdrs

    def condition_header(self, hdr):
        return { key:utils.condition_value(hdr[key]) if hdr[key] is not None else "UNDEFINED" for key in hdr }

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

def bind_assoc_to_product(product_field):
    """Guess they didn't keep the process of joining the association level
    table to the product tables simple, or document it.
    """
    return sql_or(
        sql_eq("assoc_member.asm_asn_id", product_field),
        sql_eq("assoc_member.asm_member_name", product_field),
        # sql_and(
            # sql_eq("assoc_member.asm_member_name", product_field),
            # sql_like("assoc_member.asm_member_name", "%1"),
            # sql_ne("assoc_member.asm_asn_id", "assoc_member.asm_member_name"),
        #    )
        )

def sql_or(*clauses):
    return "(" + " OR ".join(clauses) + ")"
        
def sql_and(*clauses):
    return "(" + " AND ".join(clauses) + ")"

def sql_eq(*clauses):
    return "(" + " = ".join(clauses) + ")"

def sql_ne(*clauses):
    return "(" + " != ".join(clauses) + ")"

def sql_like(a, b):
    return "({} LIKE '{}')".format(a, b)
        
def sql_in(field, ids):
    """Return a SQL IN clause such that `field` is IN the `ids`,  or
    a clause which evaluates to False if `ids` is empty.
    """
    if ids:
        return "({} IN ({}))".format(field, sql_comma_ids(ids))
    else:
        return "({} IN ('DUMMY'))".format(field)

def sql_comma_ids(ids):
    """
    Given ["A", "B", "C"] returns "'A', 'B', 'C'"
    """
    return ", ".join(["'{}'".format(did) for did in ids])

class HstHeaderGenerator(HeaderGenerator):

    def __init__(self, *args, **keys):
        HeaderGenerator.__init__(self, *args, **keys)
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

        self.product_column = self.h_to_db["data_set"]
        self.exposure_column = self.h_to_db["data_set_exp"]

        self.product_table = self.col_to_table(self.product_column)

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

    def get_headers(self, unassoc_extra_clauses=(), assoc_extra_clauses=()):
        headers = self._unassoc_get_headers(unassoc_extra_clauses)
        if self.exposure_tables:
            headers.update(self._assoc_get_headers(assoc_extra_clauses))
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
                clause = bind_assoc_to_product("{}_data_set_name".format(tab_prefix))
                clauses.append(clause)
            else:
                for field in ["program_id", "obset_id", "obsnum"]:
                    clause = "({}_{} = {}_{})".format("assoc_member.asm", field, tab_prefix, field)
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
    
    def get_dataset_ids(self, extra_clauses=()):
        return sorted(self._assoc_get_ids(extra_clauses) + self._unassoc_get_ids(extra_clauses))

    def _assoc_get_ids(self, extra_clauses=()):
        return self._make_ids(self._assoc_get_id_sql(extra_clauses))

    def _unassoc_get_ids(self, extra_clauses=()):
        return self._make_ids(self._unassoc_get_id_sql(extra_clauses))

    def _make_ids(self, sql):
        return list(set([row[0] + ":" + row[1] for row in self.catalog_db.execute(sql)]))

    def _assoc_get_id_sql(self, extra_clauses=()):
        # ID columns are the fields used to create "dataset ids".
        id_columns = ["assoc_member.asm_asn_id", "assoc_member.asm_member_name"]
        return self._getter_sql(id_columns, self.assoc_tables, 
                                tuple(self._assoc_join_clauses()) + extra_clauses)

    def _unassoc_get_id_sql(self, extra_clauses=()):
        # ID columns are the fields used to create "dataset ids".
        id_columns = [self.h_to_db["data_set"], self.h_to_db["data_set"]]
        return self._getter_sql(id_columns, self.unassoc_tables, 
                                tuple(self._unassoc_join_clauses()) + extra_clauses)

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
    try:
        return HEADER_GENERATORS[instrument.lower()]
    except:
        raise crds.CrdsError("CRDS access to DADSOPS database for instrument '{}' failed.".format(instrument.upper()))
        
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
def get_dataset_headers_by_instrument(instrument, datasets_since=None):
    """Get the header for a particular dataset,  nominally in a context where
    one only cares about a small list of specific datasets.
    """
    if datasets_since is None:
        datasets_since = "1900-01-01 00:00:00"
    init_db()
    _check_instrument(instrument)
    _check_date(datasets_since)
    try:
        igen = get_instrument_gen(instrument)
        extra_clauses = [ igen.get_expstart_clause(datasets_since) ] if datasets_since else []
        return igen.get_headers(extra_clauses, extra_clauses)
    except Exception as exc:
        raise crds.CrdsError("Error accessing catalog for instrument" + repr(instrument) + ":" + str(exc))

# ---------------------------------------------------------------------------------------------------------
"""
Here's the strategy for ID specification as-of now, it may evolve:

Fully specified ID's are of the form <product>:<member>.   <product>'s are defined
by data_set_name (and/or program_id, obset_id, obsnum) in the ref_data table for an instrument.

Since there is no "destructive" overlap between <product> and <member>,  it's also
possible to ask for <product> or <member> in a partially specified ID with no colon.
(for unassociated exposures,  <product> == <member>,  but the resulting header is the same
for both. that's "non-destructive" overlap.)  Because associations can have unique inputs
and results for each exposure,  compound ids are used to report results.  For symmetry,
unassociated products have compound ids with the same exposure and product ids,  just 
as they appear in the tables (and unfortinuately,  not in the assoc_member table).

Asking for <product> will return <product>:<member> for all associated members.

Asking for <member> will return <product>:<member> just for <member>.

In the case of unassociated exposures,  <member> == <product>, so <member>:<member> is returned.

The query works by constraining the "data_set" column to be in [<products>, ...].

data_set always corresponds to data_set_name in the product level ref_data table.

data_set will join either to exposure level tables for unassociated exposures,  or to the
association table asm_asn_id for associated exposures.   associated exposures further join
to exposure tables via asm_member_name which takes the place of data_set_name.

In both cases,  the bulk of the query constraint comes from the table join.  A tertiary
aspect of constraint is to ensure that only requested product exposures are returned.

Since for unassociated exposures, <product> == <member>,  it's enough to constrain on <product>
to get all matching headers.

"""

def get_dataset_headers_by_id(context, dataset_ids):
    """Based on a list of `dataset_ids`,  return the corresponding DADSOPS bestrefs matching parameters."""

    # _check_context(context)

    for did in dataset_ids:
        _check_dataset_id(did)

    init_db()
    
    datasets = sorted([did.upper() for did in set(dataset_ids)])
    products = sorted(list(set([ did.split(":")[0] for did in datasets ])))

    by_instrument = defaultdict(list)
    for product in products:
        instrument = dataset_to_instrument(product)
        by_instrument[instrument].append(product)

    all_headers = {}
    for instrument, products in list(by_instrument.items()):
        try:
            igen = get_instrument_gen(instrument)
            assoc_clauses, unassoc_clauses = dataset_ids_clauses(dataset_ids, igen)
            headers = igen.get_headers(
                unassoc_extra_clauses = unassoc_clauses,
                assoc_extra_clauses = assoc_clauses)
        except Exception as exc:
            raise crds.CrdsError("Error accessing catalog for instrument " + repr(instrument) + ":" + str(exc))
        all_headers.update(headers)

    products = [ cid.split(":")[0] for cid in all_headers ]
    exposures = [ cid.split(":")[1] for cid in all_headers ]
    combined = list(all_headers.keys())
    found_ids  = set(products + exposures + combined)

    missing = [ did for did in datasets if did not in found_ids and not assoc_assoc_id(did) ]

    all_headers.update( { did : "NOT FOUND no match found in query" for did in missing } )

    return all_headers

def assoc_assoc_id(id):
    """Return True IFF the ID is of the form <assoc>:<assoc>."""
    parts = id.split(":")
    return len(parts) == 2 and parts[0] == parts[1] and parts[0].endswith("0")

class InvalidDatasetIdError(RuntimeError):
    """The format of a dataset id is bad."""

def dataset_ids_clauses(dataset_ids, igen): # assoc_field, unassoc_field):
    """Compute SQL to constrain returned datasets to specific ID list.

    dataset_ids  [ dataset_id, ...]
    products_field   SQL <table>.<field> where product ids are found
    exposures_field  SQL <table>.<field> where exposure/member ids are found

    Dataset IDs are of these forms:
    1. <product>  (ends in 0 or 1)
    2. <exposure>
    3. <product>:<product>  == <exposure>:<exposure> (unassociated)
    3. <product>:<exposure> (associated)

    Returns "<product_clause> OR <exposure_clause>"

    This works on the principle that the product_clause is a weaker constaint
    than the exposure clause and unassociated exposures can be specified 
    "either way".  Adding an ID to the products list will return every member
    of the association.   Adding and ID to the exposures list will only return
    that exposure.  The basic query constrained by these clauses returns all
    associated and unassociated exposures.

    All members/exposures of products in <product_clause> are returned.

    Only the explicitly mentioned exposure in <exposure_clause> is returned.
    
    If both the vague and explict forms of associated exposures are specified,
    the vague ID is fully interpreted and ALL memnbers should be returned.

    If only explicit form of associated exposures are used,  then only the
    explicitly requested exposures should be returned.

    NOTE: member_name is only available for associated exposures.
    """
    assoc_set, member_set = set(), set()
    for did in dataset_ids:
        parts = did.split(":")
        if len(parts) == 1:
            assoc_set.add(did)  # works either way
            member_set.add(did)
        elif len(parts) == 2:
            assoc, member = parts
            # assoc_set.add(assoc)
            member_set.add(member)        
        else:
            raise InvalidDatasetIdError("Compound dataset ids have 1-2 parts separated by a colon.")
    
    bind_product_col_to_exposure_col = sql_eq(igen.product_column, igen.exposure_column)
    bind_product_to_combined_set = sql_in(igen.product_column, assoc_set.union(member_set))
    unassoc_clauses = (
        bind_product_col_to_exposure_col,
        bind_product_to_combined_set)

    # Determine associated clauses,  STIS seems to violate the norm of joining asm_member_name to
    # igen.exposure_col,  joining instead igen.product_col.  However,  member_names still exist,
    # so it'd be nice to be able to pick those up
    if igen.instrument == "stis":
        bind_assoc_to_product_col = sql_eq("assoc_member.asm_asn_id", igen.product_column)
        bind_asn_id_to_assoc_set = sql_in("assoc_member.asm_asn_id", assoc_set)
        bind_asn_member_to_member_set = sql_in("assoc_member.asm_member_name", member_set)
        assoc_clauses = (
            bind_assoc_to_product_col,
            sql_or(bind_asn_id_to_assoc_set, bind_asn_member_to_member_set)
            )
    else:
        bind_product_col_to_assoc_set = sql_in(igen.product_column, assoc_set)
        bind_exposure_col_to_member_set = sql_in(igen.exposure_column, member_set)
        bind_assoc_to_product_col = bind_assoc_to_product(igen.product_column)
        bind_asn_member_to_exposure_col = sql_eq("assoc_member.asm_member_name", igen.exposure_column)
        bind_product_exposure_cols_to_id_sets = sql_or(bind_product_col_to_assoc_set, bind_exposure_col_to_member_set)
        assoc_clauses = (
            bind_assoc_to_product_col,
            bind_asn_member_to_exposure_col,
            bind_product_exposure_cols_to_id_sets
            )

    return assoc_clauses, unassoc_clauses

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
    headers = { did : source_headers[src_id] for (did, (src_id, typ, ctype)) in list(id_map.items()) if src_id in source_headers }
    return headers

# This is a table of the assoc_member.asm_member_type correspondence rules
# where keys are assumed to be "unrepresented" types and values are assumed
# to fully resolve in DADSOPS producing workable headers for that member.
# The workable member is used as a surrogate for the unrepresented member.

CORRESPONDING_TYPE = {                      
    "PRODUCT"   : "SCIENCE",

    "PROD-DTH"  : "EXP-DTH",
    "PROD-TARG" : "EXP-TARG",
    'PROD-CRJ'  : 'EXP-CRJ', 
    'PROD-RPT'  : 'EXP-RPT', 
    'PROD-FP'   : 'EXP-FP', 
    
    'PROD-BCK1' : 'EXP-BCK1', 
    'PROD-BCK2' : 'EXP-BCK2', 
    'PROD-BCK3' : 'EXP-BCK3', 
    'PROD-BCK4' : 'EXP-BCK4', 
    
    'PROD-CR1'  : 'EXP-CR1', 
    'PROD-CR2'  : 'EXP-CR2', 
    'PROD-CR3'  : 'EXP-CR3',
    'PROD-CR4'  : 'EXP-CR4', 
    'PROD-CR5'  : 'EXP-CR5', 
    'PROD-CR6'  : 'EXP-CR6', 
    'PROD-CR7'  : 'EXP-CR7', 
    'PROD-CR8'  : 'EXP-CR8', 
    'PROD-CR9'  : 'EXP-CR9', 
    'PROD-CR10' : 'EXP-CR10', 
    'PROD-CR11' : 'EXP-CR11', 
    'PROD-CR12' : 'EXP-CR12', 
     
     'PROD-RP1'  : 'EXP-RP1', 
     'PROD-RP2'  : 'EXP-RP2', 
     'PROD-RP3'  : 'EXP-RP3', 
     'PROD-RP4'  : 'EXP-RP4', 
     'PROD-RP5'  : 'EXP-RP5',  
     'PROD-RP6'  : 'EXP-RP6', 
     'PROD-RP7'  : 'EXP-RP7', 
     'PROD-RP8'  : 'EXP-RP8', 
     'PROD-RP9'  : 'EXP-RP9', 
     'PROD-RP10' : 'EXP-RP10', 
     'PROD-RP11' : 'EXP-RP11', 
     'PROD-RP12' : 'EXP-RP12', 
}

def get_synthetic_id_map(dataset_ids):
    """Given a list of arbitrary dataset ids,  compute the list of equivalent ids
    which the incoming ids map to.   This supports using surrogate parameters for
    intermediate products which aren't fully represented in the database.  It's
    hideous and I was a victim too...

    Returns { incoming_id : (workable_id, incoming_type, workable_type), ... }

    The mapping of incoming_type : workable_type indicates which member was substituted
    for which in a visually comprehensible manner.
    """
    cat = get_catalog()

    assocs, members = partition_dataset_ids(dataset_ids)

    member_assocs = cat.lexecute("SELECT asm_asn_id, asm_member_name, asm_member_type"
                                 " FROM assoc_member WHERE {}".format(sql_in("asm_member_name", members)))

    asn_ids = sorted([ tup[0] for tup in member_assocs ] + assocs)
    assocs = cat.lexecute("SELECT asm_asn_id, asm_member_name, asm_member_type"
                          " FROM assoc_member WHERE {}".format(sql_in("asm_asn_id", asn_ids)))

    type_mapping = defaultdict(dict)
    for (assoc, member, typ) in reversed(assocs):
        type_mapping[assoc][typ] = member

    new_ids = {}
    for did in dataset_ids:
        for (assoc, member, typ) in assocs:
            if did in [assoc, member, compound_id(assoc, member)]:
                if typ not in list(CORRESPONDING_TYPE.keys()):
                    ctype = typ
                    corresponding_member = member
                else:
                    ctype = CORRESPONDING_TYPE[typ]
                    corresponding_member = type_mapping[assoc].get(ctype, member)
                new_ids[compound_id(assoc, member)] = (compound_id(assoc, corresponding_member), typ, ctype)

    for did in dataset_ids:
        for compound in list(new_ids.keys()):
            if did in compound:
                break
        else: # Add in unassociated exposures as-is
            if ":" not in did:
                new_ids[compound_id(did, did)] = (compound_id(did, did), "UNASSOC", "UNASSOC")
            else:
                new_ids[did] = (did, "UNASSOC", "UNASSOC")

    return new_ids

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

    if instrument.lower() == "synphot":
        return []

    init_db()

    igen = get_instrument_gen(instrument)
    extra_clauses = tuple([ igen.get_expstart_clause(datasets_since) ] if datasets_since else [])

    return igen.get_dataset_ids(extra_clauses)

# ----------------------------------------------------------------------------------------------------------
def get_normalized_ids(dataset_ids):
    return [did.upper() for did in dataset_ids]
