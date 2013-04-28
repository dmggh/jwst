"""This module accesses non-Django supporting databases using pyodbc,
unixODBC,  and FreeTDS,  to get dataset headers from the HST DADSOPS 
catalog.
"""
import pprint
import getpass
from collections import OrderedDict, defaultdict
import os.path

import pyodbc

from crds import rmap, log, utils, timestamp
from crds.server.interactive import models

if models.OBSERVATORY == "hst":
    import crds.hst
    import crds.hst.parkeys as parkeys

log.set_verbose(False)

HERE = os.path.dirname(__file__) or "."
HEADER_TABLES = HERE + "/db_header_tables.dat"
PASSWORD_FILE = HERE + "/db_password.dat"

"""  
IPPPSSOOT   ---   dataset naming breakdown

Denotes the instrument type:
J - Advanced Camera for Surveys
U - Wide Field / Planetary Camera 2
V - High Speed Photometer
W - Wide Field / Planetary Camera
X - Faint Object Camera
Y - Faint Object Spectrograph
Z - Goddard High Resolution Spectrograph
E - Reserved for engineering data
F - Fine Guide Sensor (Astrometry)
H-I,M - Reserved for additional instruments
N - Near Infrared Camera Multi Object Spectrograph
O - Space Telescope Imaging Spectrograph
S - Reserved for engineering subset data
T - Reserved for guide star position data
PPP     Denotes the program ID, any combination of letters or numbers
SS    Denotes the observation set ID, any combination of letters or numbers
OO    Denotes the observation ID, any combination of letters or numbers
T    Denotes the source of transmission:
R - Real time (not tape recorded)
T - Tape recorded
M - Merged real time and tape recorded
N - Retransmitted merged real time and tape recorded
O - Retransmitted real time
P - Retransmitted tape recorded
"""

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

def dataset_to_instrument(dataset):
    instr = dataset[0].upper()
    try:
        return IPPPSSOOT_INSTR[instr]
    except KeyError:
        raise ValueError("Can't determine instrument for dataset " + repr(dataset))

class DB(object):
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

    def get_tables(self):
        return [row.table_name for row in self.cursor.tables()]

    def get_columns(self, table):
        return [col.column_name for col in self.cursor.columns(table=table)]

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

        for row in self.execute("select %s from %s %s" % (col_names, table, where)):
            items = zip(col_list, [str(x).lower() for x in row] if lowercase else row)
            kind = OrderedDict if ordered else dict
            yield kind(items)

def get_password():
    if not hasattr(get_password, "_password"):
        try:
            get_password._password = open(PASSWORD_FILE).read().strip()
        except:
            get_password._password = getpass.getpass("password: ")
    return get_password._password

def get_dadsops(user="jmiller"):
    """Cache and return a database connection to DADSOPS."""
    if not hasattr(get_dadsops, "_dadsops"):
        get_dadsops._dadsops = DB("HarpoDadsopsRepDsn", user, get_password())
    return get_dadsops._dadsops

def get_reffile_ops(user="jmiller"):
    """Cache and return a database connection to REFFILE_OPS."""
    if not hasattr(get_reffile_ops, "_reffile_ops"):
        get_reffile_ops._reffile_ops = DB("HarpoReffileOpsRepDsn", user, get_password())
    return get_reffile_ops._reffile_ops

def get_instrument_db_parkeys(instrument):
    """Return the union of the database versions of all parkeys for all
    filekinds of instrument.
    """
    dbkeys = set()
    for filekind in parkeys.get_filekinds(instrument):
        dbkeys = dbkeys.union(set(parkeys.get_db_parkeys(instrument, filekind)))
        dbkeys = dbkeys.union(set(parkeys.get_extra_keys(instrument, filekind)))
    return list(dbkeys)

def required_keys(instr):
    """Get both the input parkeys and expected results keywords for
    all filekinds of `instr`ument`.
    """
    pars = get_instrument_db_parkeys(instr)
    pars.append("expstart" if instr != "stis" else "texpstrt")
    pars.append("data_set")
    imap = rmap.get_cached_mapping("hst_%s.imap" % instr)
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
    instrument against the available instrument tables and columns in DADSOPS,
    returning a map  { parameter : [ "table.column", ...] } finding plausible
    locations for each CRDS best refs parameter in the dataset catalog.
    """
    dadsops = get_dadsops()
    pars = required_keys(instr)
    columns = {}
    for table in dadsops.get_tables():
        if instr not in table:
            continue
        for par in pars:
            for col in dadsops.get_columns(table):
                if par in col:
                    if par not in columns:
                        columns[par] = []
                    columns[par].append(table + "." + col)
    return columns, set(pars) - set(columns.keys())

"""
SELECT Persons.LastName, Persons.FirstName, Orders.OrderNo
FROM Persons
FULL JOIN Orders
ON Persons.P_Id=Orders.P_Id
ORDER BY Persons.LastName

select * from table where name in (word1,word2,word3)
"""

class HeaderGenerator(object):
    def __init__(self, instrument, catalog_db, header_to_db_map):
        self.instrument = instrument.lower()
        self.catalog_db = catalog_db        
        self.h_to_db = header_to_db_map

    @property
    def header_keys(self):
        return [key.upper() for key in self.h_to_db.keys()]

    @property
    def db_columns(self):
        return self.h_to_db.values()

    @property
    def db_tables(self):
        tables = set()
        for column in self.db_columns:
            table, col = column.split(".")
            tables.add(table)
        return list(tables)

    @property
    def all_columns(self):
        all_cols = []
        for table in self.db_tables:
            all_cols += [table + "." + col for col in self.catalog_db.get_columns(table)]
        return all_cols

    def getter_sql(self, extra_constraints={}, extra_clauses=()):
        sql = "SELECT %s FROM %s " % (", ".join(self.db_columns), ", ".join(self.db_tables))
        clauses = self.join_clauses() 
        if extra_constraints:
            clauses.extend(self.constraint_clauses(extra_constraints))
        clauses.extend(list(extra_clauses))
        sql += "WHERE " + (" AND ").join(clauses)
        return sql

    def join_clauses(self, join_suffices=("program_id", "obset_id", "obsnum")):
        clauses = []
        if len(self.db_tables) < 2:
            return clauses
        for suffix in join_suffices:
            joined = []
            for col in self.all_columns:
                if col.endswith(suffix):
                    joined.append(col)
            if len(joined) >= 2:
                for more in joined[1:]:
                    clauses.append(joined[0] + "=" + more)
        return clauses

    def constraint_clauses(extra_constraints):
        for key in extra_constraints:
            for col in self.all_columns:
                if key.lower() in col:
                    break
            else:
                raise ValueError("No db column found for constraint " + repr(key))
            clauses.append(col + "=" + repr(extra_constraints[key]))
        return clauses

    def get_headers(self, extra_constraints={}, extra_clauses=(), condition=True):
        sql = self.getter_sql(extra_constraints, extra_clauses)
        for dataset in self.catalog_db.execute(sql):
            hdr = dict(zip(self.header_keys, list(dataset)))
            if condition:
                hdr = { key:utils.condition_value(hdr[key]) for key in hdr }
            hdr = self.fix_hdr(hdr)
            yield hdr

    def fix_hdr(self, hdr):
        hdr["INSTRUME"] = self.instrument.upper()
        hdr = dict(hdr)
        expstart = hdr.get("EXPSTART", hdr.get("TEXPSTRT"))
        try:
            hdr["DATE-OBS"], hdr["TIME-OBS"] = timestamp.format_date(expstart).split()
        except:
            log.warning("Bad database EXPSTART", expstart)
        return hdr 

    def get_dataset_ids(self):
        return list(igen.catalog_db.execute("SELECT {} FROM {}".format(self.h_to_db["data_set"], self.db_tables)))

HEADER_MAP = None
HEADER_GENERATORS = {}

def init_db():
    global HEADER_MAP, HEADER_TABLES, HEADER_GENERATORS
    if HEADER_MAP is None:
        with log.error_on_exception("Failed loading", repr(HEADER_TABLES)):
            HEADER_MAP = eval(open(HEADER_TABLES).read())
            with log.error_on_exception("Failed getting catalog connection"):
                connection = get_dadsops()
                with log.error_on_exception("Failed setting up header generators"):
                    HEADER_GENERATORS = {}
                    for instr in HEADER_MAP:
                        HEADER_GENERATORS[instr] = HeaderGenerator(instr, connection, HEADER_MAP[instr])


def get_dataset_header(dataset, observatory="hst"):
    """Get the header for a particular dataset,  nominally in a context where
    one only cares about a small list of specific datasets.
    """
    init_db()
    return get_dataset_headers([dataset], observatory)

def get_dataset_headers(datasets, observatory="hst"):
    """Get the header for a particular dataset,  nominally in a context where
    one only cares about a small list of specific datasets.
    """
    init_db()
    datasets = sorted(list(set(datasets)))
    by_instrument = defaultdict(list)
    for dataset in datasets:
        instrument = dataset_to_instrument(dataset)
        by_instrument[instrument].append(dataset)
    all_headers = {}
    for instrument, datasets in by_instrument.items():
        try:
            igen = HEADER_GENERATORS[instrument]
            dataset_column = igen.h_to_db["data_set"]
            dataset_ids = ", ".join(["'{}'".format(id.upper()) for id in datasets])
            datasets_clause = "{} in ({})".format(dataset_column, dataset_ids)
            headers = { hdr["DATA_SET"]:hdr for hdr in igen.get_headers(extra_clauses=[datasets_clause]) }
        except Exception, exc:
            raise RuntimeError("Error accessing catalog for dataset " + repr(dataset) + ":" + str(exc))
        all_headers.update(headers)
    return all_headers

def get_dataset_ids(instrument, observatory="hst"):
    """Return a list of the known dataset ids for `instrument`."""
    init_db()
    igen = HEADER_GENERATORS[instrument]
    return igen.get_dataset_ids()
