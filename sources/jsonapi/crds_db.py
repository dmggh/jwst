"""This module support dumping the CRDS database as a SQLite3 file so that it
can be distributed.
"""
import tempfile

from crds.core import pysh, config
from crds_server.crds_database import DATABASES

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
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_path = temp_file.name
    temp_file.close()
    pysh.sh("convert_db -u'${user}' -p'${password}' --host='${host}' --port=$port --databases ${database} --tables ${tables} | sqlite3 ${temp_path}")  # secured.
    pysh.sh("mv ${temp_path} ${db_path}") # secured.
    return db_path
