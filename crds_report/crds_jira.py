import sys
import getpass
import datetime
import os.path

# =================================================================

import jira   # current recommendation "pip install jira"

# =================================================================

import crds_rst

# =================================================================

PROJECT = "CCD"
HOST = "https://jira.stsci.edu"

def format_date(datestr):
    return datestr.split("T")[0]

FIELDS = [
    ("Issue", "key", crds_rst.link_use_rst),
    ("Status", "fields.status"),
    ("Resolution", "fields.resolution"),
    ("Type", "fields.issuetype"),
    ("Priority", "fields.priority"),
    # ("Target Build", "fields.targetbuild"),
    ("Summary", "fields.summary"),
    ("Created",  "fields.created", format_date),
    ("Resolved", "fields.resolutiondate", format_date),
]

FIELD_NAMES = [ field[0] for field in FIELDS ]

JIRA_AUTHENTICATION_INFO = "/crds/data1/database/jira_auth_info.txt"

# =================================================================

def issue_url(key):
    return HOST + "/projects/" + PROJECT + "/issues/" + key + "?filter=allissues"

# =================================================================

class JiraConnection(object):

    def __init__(self, days_back, fields=FIELDS, basic_auth=None):
        if os.path.exists(JIRA_AUTHENTICATION_INFO):
            with open(JIRA_AUTHENTICATION_INFO) as auth_info:
                user = auth_info.readline().strip()
                passwd = auth_info.readline().strip()
        elif basic_auth is None:
            user = getpass.getuser()   # also user env var LOGNAME or USERNAME
            passwd = getpass.getpass()
        self.since_date = (datetime.datetime.now() + datetime.timedelta(days=days_back)).isoformat().split(".")[0]
        basic_auth = (user, passwd)
        self.connection = jira.JIRA(HOST, basic_auth=basic_auth)
        self.fields = fields
        self.rows = self.get_rows()
                           
    def issue_selector(self, issue):
        status = str(issue.fields.status)
        resolution = str(issue.fields.resolution)
        resolution_date = str(issue.fields.resolutiondate).split("T")[0]
        select = status in ["In Progress"]
        select = select or ((status.upper() in ["CLOSED","RESOLVED","REOPENED","FIXED","READY FOR TESTING"]) and resolution_date >= self.since_date)
        return select

    def _load_basic_auth(self, auth_path):
        return tuple(open(auth_path).read().splitlines()[0].split(","))

    @property
    def issues(self):
        return self.connection.search_issues(f"project={PROJECT}", maxResults=10**9)

    def get_rows(self):
        issues = self.issues
        names = [ field[0] for field in self.fields ]
        rows = [names]
        for issue in self.issues:
            if not self.issue_selector(issue):
                continue
            row = [ self.resolve_field(issue, field)
                    for field in self.fields ]
            rows.append(row)
        return list(sorted(rows))

    def resolve_field(self, issue, field):
        val = issue
        for attr in field[1].split("."):
            val = getattr(val, attr)
        val = str(val)
        if len(field) == 3:
            val = field[2](val)
        return str(val)

    @property
    def table(self):
        table = crds_rst.CrdsTable(
            "CRDS Development",
            self.rows[0],
            self.rows[1:]
        )
        return table

    def to_rst(self):
        table = self.table.to_rst()
        link_defs = []
        for row in self.rows[1:]:
            name = crds_rst.unlink_rst(row[0])
            url = issue_url(name)
            link_defs.append(crds_rst.link_def_rst(name, url))
        link_defs = "\n".join(link_defs)
        return table + "\n" + link_defs + "\n"
                                   
def main(days_back, fields=FIELD_NAMES):
    days_back = int(days_back)
    field_dict = { field[0] : field for field in FIELDS }
    reduced_fields = [ field_dict[field] for field in fields]
    j = JiraConnection(days_back, reduced_fields)
    print(j.to_rst())

if __name__ == "__main__":
    days_back = sys.argv[1]
    fields = sys.argv[2].split(",") if len(sys.argv) > 2 else FIELD_NAMES
    main(days_back, fields)
