#! /usr/bin/env python
#-*- python

# ==============================================================================

import sys
import os
import os.path
import re
import datetime

# ==============================================================================

from crds.core import log

from crds.client import api

import crds_rst

# ==============================================================================

# XXXX duplicated in crds_jira.py
DEFAULT_SINCE_DATE = (datetime.datetime.now() + datetime.timedelta(days=-7)).isoformat().split(".")[0]

# ==============================================================================

def get_delivery_status(since_date=DEFAULT_SINCE_DATE):
    """Return a list of delivery status dictionaries for deliveries which occurred
    after `self.since_date`.
    """
    return api.S.get_delivery_status(since_date)

# ==============================================================================

class ServerStatus(object):
    def __init__(self, observatory, usecase, url, since_date=DEFAULT_SINCE_DATE):
        self.observatory = observatory
        self.usecase = usecase
        self.url = url
        self.since_date = since_date
        self.link_defs = []
        api.set_crds_server(self.url)
        os.environ["CRDS_OBSERVATORY"] = observatory

    def to_rst(self):
        return self.title_rst() + "\n" + \
            self.delivery_rst() + "\n" + \
            self.context_rst() + "\n" + \
            self.support_rst() + "\n" + \
            self.link_defs_rst()

    # ---------------------------------------------------------------------

    def add_context_links(self, index, rows):
        rst_rows = []
        for row in rows:
            context_name = row[index]
            context_use_rst = crds_rst.link_use_rst(context_name)
            row = row[:index] + (context_use_rst,) + row[index+1:]
            rst_rows.append(row)
            context_link = self.url + "/context_table/" + context_name
            self.add_link_def(context_name, context_link)
        return rst_rows

    def add_link_def(self, name, url):
        link_def = crds_rst.link_def_rst(name, url)
        if link_def not in self.link_defs:
            self.link_defs.append(link_def)

    def link_defs_rst(self):
        return "\n".join(self.link_defs) + "\n"

    # ---------------------------------------------------------------------

    def title_rst(self):
        title = "CRDS " + self.observatory.upper() + " " + self.usecase.upper()
        return crds_rst.underline(title, "-")

    def support_rst(self):
        OBS = self.observatory.upper()
        URL = self.url
        return f"""
Links
+++++

`{OBS} Server`_

`{OBS} Default Context History`_

`{OBS} All Contexts`_

`{OBS} User's Guide`_

.. _`{OBS} Server`: {URL}
.. _`{OBS} Default Context History`:  {URL}/display_context_history/
.. _`{OBS} All Contexts`:  {URL}/display_all_contexts/
.. _`{OBS} User's Guide`: {URL}/static/users_guide/index.html
"""

    # ---------------------------------------------------------------------

    def context_info(self):
        names = ["Location", "Context", "Notes"]
        rows = [
            ("Last Delivered", api.get_context_by_date(self.observatory + "-edit"),  
             "AKA the 'edit' context."),
            ]
        if self.observatory != "jwst":
            rows += [
            ("Pipeline", api.get_remote_context(self.observatory, self.observatory + "-ops-pipeline"), 
             "In use by the archive, lags Last Delivered."),
                ]
        rows += [
            ("Onsite Default", api.get_remote_context(self.observatory, "/grp/crds/cache"), 
             "AKA /grp/crds/cache.   Used by users with no CRDS_PATH and CRDS_SERVER_URL."),
            ("Server Default, Offsite", api.get_context_by_date(self.observatory + "-operational"), 
             "Used by private caches, requires CRDS_PATH and CRDS_SERVER_URL."),
           ]
        return (names, rows)

    def context_rst(self):
        names, rows = self.context_info()
        rst_rows = self.add_context_links(1, rows)
        table = crds_rst.CrdsTable("Context Settings", names, rst_rows, format=("+","="))
        return table.to_rst() + "\n" 

    # ---------------------------------------------------------------------

    delivery_fields = "date,context,status,description".split(",")

    def delivery_info(self):
        try:
            deliveries = get_delivery_status(self.since_date)
        except Exception as exc:
            log.error("Failed obtaining delivery status:", str(exc))
            return (),()
        deliveries = self.clean_deliveries(deliveries)
        rows = [ self.get_row(delivery) for delivery in deliveries ]
        names = [name.capitalize() for name in self.delivery_fields]
        return names, rows

    def get_row(self, delivery):
        return tuple(delivery[name] for name in self.delivery_fields)

    def clean_deliveries(self, deliveries):
        cleaned = []
        for delivery in deliveries:
            clean = dict(delivery)
            clean["date"] = delivery["date"].split(" ")[0]
            clean["context"] = [ file for file in delivery["files"]
                                 if file.endswith(".pmap")][0]
            cleaned.append(clean)
        return cleaned

    def delivery_rst(self):
        names, rows = self.delivery_info()
        if not names:
            return ""
        rst_rows = self.add_context_links(1, rows)
        table = crds_rst.CrdsTable(
            "Deliveries", names, rst_rows, format=("+","="))
        return table.to_rst() + "\n"

# ==============================================================================

def main(observatory, usecase, url):
    status = ServerStatus(observatory, usecase, url)
    print(status.to_rst())

if __name__ == "__main__":
    main(*sys.argv[1:])

