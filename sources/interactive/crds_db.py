"""This module support dumping the CRDS database as a SQLite3 file so that it
can be distributed.
"""

from crds import pysh, config
from crds.server.crds_database import DATABASES

def dump_sqlite_db(observatory):
    """Dump the CRDS database to a SQLite db file in the CRDS cache config directory."""
    db = DATABASES["default"]
    database = db["NAME"]
    user = db["USER"]
    password = db["PASSWORD"]
    host = db["HOST"]
    port = db["PORT"]
    prefix = "crds_" + observatory + "_"
    tables = " ".join([prefix + table for table in ["catalog", "context_history"]])
    db_path = config.get_sqlite3_db_path(observatory)
    pysh.sh("convert_db -u'${user}' -p'${password}' --host='${host}' --port=$port --databases ${database} --tables ${tables} | sqlite3 ${db_path}")  # secured.
    return db_path
