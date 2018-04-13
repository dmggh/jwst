#! /usr/bin/env python
#-*- python

# ==============================================================================

import sys
import os
import os.path
import re
import datetime

# ==============================================================================

from crds.client import api

import crds_rst

# ==============================================================================

DEFAULT_SINCE_DATE = (datetime.datetime.now() + datetime.timedelta(days=-14)).isoformat().split(".")[0]

DEFAULT_FIELDS = "date,context,status,description".split(",")

# ==============================================================================

class ServerStatus(object):
    def __init__(self, observatory, usecase, url, 
                 since_date=DEFAULT_SINCE_DATE,
                 delivery_fields=DEFAULT_FIELDS):
        self.observatory = observatory
        self.usecase = usecase
        self.url = url
        self.since_date = since_date
        self.delivery_fields = delivery_fields
        api.set_crds_server(self.url)
        os.environ["CRDS_OBSERVATORY"] = observatory

    def to_rst(self):
        return self.context_rst() + "\n" + \
            self.delivery_rst() + "\n" + \
            self.links_rst() + "\n"

    def links_rst(self):
        OBS = self.observatory.upper()
        URL = self.url
        return f"""
`{OBS} Server`_

`{OBS} Default Context History`_

`{OBS} All Contexts`_

.. _`{OBS} Server`: {URL}
.. _`{OBS} Default Context History`:  {URL}/display_context_history/
.. _`{OBS} All Contexts`:  {URL}/display_all_contexts/
"""

    def context_info(self):
        names = ["Location", "Context"]
        rows = [
            ("Delivered", api.get_context_by_date(self.observatory + "-edit")),
            ("Server Default", api.get_context_by_date(self.observatory + "-operational")),
            ("Onsite User", api.get_remote_context(self.observatory, "/grp/crds/cache")),
            ("Pipeline", api.get_remote_context(self.observatory, self.observatory + "-ops-pipeline")),
         ]
        return (names, rows)

    def context_rst(self):
        names, rows = self.context_info()
        rst_rows = []
        link_defs = ""
        for row in rows:
            rst_rows.append((row[0], crds_rst.link_use_rst(row[1])))
            link_url = self.url + "/context_table/" + row[1]
            link_def = crds_rst.link_def_rst(row[1], link_url)
            link_defs += link_def + "\n"
        title = self.observatory.upper() + " Status"
        table = crds_rst.CrdsTable(title, names, rst_rows)
        rst = table.to_rst() + "\n"
        rst += link_defs
        return rst

    def get_delivery_status(self):
        """Return a list of delivery status dictionaries for deliveries which occurred
        after `self.since_date`.
        """
        return api.S.get_delivery_status(self.since_date)

    def delivery_rst(self):
        try:
            deliveries = self.get_delivery_status()
        except Exception:
            return ""
        deliveries = self.clean_deliveries(deliveries)
        rows = []
        for delivery in deliveries:
            row = self.get_row(delivery)
            rows.append(row)
        title = self.observatory.upper() + " Deliveries"
        names = [name.capitalize() for name in self.delivery_fields]
        table = crds_rst.CrdsTable(title, names, rows)
        return table.to_rst()

    def get_row(self, delivery):
        return tuple(delivery[name] for name in self.delivery_fields)

    def clean_deliveries(self, deliveries):
        cleaned = []
        for delivery in deliveries:
            clean = dict(delivery)
            clean["date"] = delivery["date"].split(".")[0]
            clean["context"] = [ file for file in delivery["files"]
                                         if file.endswith(".pmap")][0]
        cleaned.append(clean)
        return cleaned

# ==============================================================================

def main(observatory, usecase, url):
    status = ServerStatus(observatory, usecase, url)
    print(status.to_rst())

if __name__ == "__main__":
    main(*sys.argv[1:])







