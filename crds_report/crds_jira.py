import sys
import getpass
import datetime

# =================================================================

import jira   # current recommendation "pip install jira"

# =================================================================

import crds_rst

# =================================================================

# XXXX duplicated from crds_server_status.py
DEFAULT_SINCE_DATE = (datetime.datetime.now() + datetime.timedelta(days=-7)).isoformat().split(".")[0]

# =================================================================

def issue_selector(issue):
    status = str(issue.fields.status)
    resolution = str(issue.fields.resolution)
    resolution_date = str(issue.fields.resolutiondate).split("T")[0]
    select = status in ["In Progress"]
    select = select or ((status in ["Closed","Resolved"]) and resolution_date >= DEFAULT_SINCE_DATE)
    return select

def issue_url(key):
    return HOST + "/projects/" + PROJECT + "/issues/" + key + "?filter=allissues"

def format_date(datestr):
    return datestr.split("T")[0]

# =================================================================

PROJECT="CCD"
HOST = "https://jira.stsci.edu"

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

# =================================================================

class JiraConnection(object):

    def __init__(self, fields=FIELDS, issue_selector=issue_selector, basic_auth=None):
        if basic_auth is None:
            user = getpass.getuser()   # also user env var LOGNAME or USERNAME
            passwd = getpass.getpass()
            basic_auth = (user, passwd)
        self.connection = jira.JIRA(HOST, basic_auth=basic_auth)
        self.fields = fields
        self.issue_selector = issue_selector
        self.rows = self.get_rows()

    def _load_basic_auth(self, auth_path):
        return tuple(open(auth_path).read().splitlines()[0].split(","))

    @property
    def issues(self):
        return self.connection.search_issues(f"project={PROJECT}")

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
                                   
def test():
    j = JiraConnection()
    print(j.to_rst())

if __name__ == "__main__":
    test()
