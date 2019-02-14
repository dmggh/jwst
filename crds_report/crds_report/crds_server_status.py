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

from . import crds_rst

# ==============================================================================

# XXXX duplicated in crds_jira.py
DEFAULT_SINCE_DATE = None

# ==============================================================================

class ServerStatus(object):
    def __init__(self, observatory, usecase, url, days_back):
        self.observatory = observatory
        self.usecase = usecase
        self.url = url
        self.link_defs = []
        self.since_date = (datetime.datetime.now() + datetime.timedelta(days=days_back)).isoformat().split(".")[0]
        api.set_crds_server(self.url)
        os.environ["CRDS_OBSERVATORY"] = observatory

    def to_rst(self):
        return self.title_rst() + "\n" + \
            self.delivery_rst() + "\n" + \
            self.context_rst() + "\n" + \
            self.support_rst() + "\n" + \
            self.link_defs_rst()

    # ---------------------------------------------------------------------

    def add_context_links(self, index, rows, base_url, prefix):
        rst_rows = []
        for row in rows:
            context_name = row[index]
            if "no context" not in context_name.lower():
                context_number = context_name.split("_")[1].split(".")[0]
                context_anchor = (self.observatory + "_" + self.usecase + 
                                  "_" + prefix + context_number)
                context_use_rst = crds_rst.link_use_rst(context_anchor)
                context_link = base_url + context_name
                self.add_link_def(context_anchor, context_link)
            else:
                context_use_rst = context_name
            row = row[:index] + (context_use_rst,) + row[index+1:]
            rst_rows.append(row)
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
        URL = self.url
        STRING = self.observatory.upper() + " " + self.usecase.upper()
        TITLE = crds_rst.underline(STRING + " Links", "+")
        return f"""
{TITLE}

`{STRING} Server`_

`{STRING} Default Context History`_

`{STRING} All Contexts`_

`{STRING} User's Guide`_

.. _`{STRING} Server`: {URL}
.. _`{STRING} Default Context History`:  {URL}/display_context_history/
.. _`{STRING} All Contexts`:  {URL}/display_all_contexts/
.. _`{STRING} User's Guide`: {URL}/static/users_guide/index.html
"""

    # ---------------------------------------------------------------------

    def context_info(self):
        names = ["Location", "Context Table", "Notes"]
        rows = [
            ("Last Delivered", api.get_context_by_date(self.observatory + "-edit"),  
             "AKA the 'edit' context new deliveries add to."),
            ]
        rows += [
            ("Server Default, Offsite", api.get_context_by_date(self.observatory + "-operational"), 
             "AKA the 'operational' context used by any system syncing to the CRDS Server."),
           ]
        if self.observatory != "jwst":
            rows += [
                ("Pipeline Echo", api.get_remote_context(self.observatory, self.observatory + "-ops-pipeline"), 
                 "The context echoed by the pipeline after its last sync to the CRDS server."),
            ]
        if self.usecase == "ops":
            rows += [
                ("Onsite Default", api.get_remote_context(self.observatory, "/grp/crds/cache"), 
                 "AKA /grp/crds/cache.   Default cache for onsite users with no CRDS_PATH and CRDS_SERVER_URL."),
            ]
        return (names, rows)

    def context_rst(self):
        names, rows = self.context_info()
        context_link = self.url + "/context_table/"
        rst_rows = self.add_context_links(1, rows, context_link, "table_")
        table = crds_rst.CrdsTable(
            self.title("Context Settings"), names, rst_rows, format=("+","="))
        return table.to_rst() + "\n" 

    def title(self, text):
        return self.observatory.upper() + " " + self.usecase.upper() + " " + text

    # ---------------------------------------------------------------------

    delivery_fields = "date,context table,actions,status,description".split(",")

    def delivery_info(self):
        try:
            deliveries = get_delivery_status(self.since_date)
        except Exception as exc:
            log.error("Failed obtaining delivery status:", str(exc))
            return (),()
        deliveries = self.clean_deliveries(deliveries)
        rows = [ self.get_row(delivery) for delivery in deliveries ]
        names = []
        for name in self.delivery_fields:
            pieces = [ piece.capitalize() for piece in name.split() ]
            names.append(" ".join(pieces))
        return names, rows

    def get_row(self, delivery):
        return tuple(delivery[name] for name in self.delivery_fields)

    def clean_deliveries(self, deliveries):
        cleaned = []
        for delivery in deliveries:
            contexts = [file for file in delivery["files"]
                        if file.endswith(".pmap")]
            context = contexts[0] if contexts else "No context generated"
            clean = dict(delivery)
            clean["date"] = delivery["date"].split(" ")[0]
            clean["context table"] = context
            clean["actions"] = context
            clean["description"] = crds_rst.quote(delivery["description"])
            cleaned.append(clean)
        return cleaned

    def delivery_rst(self):
        names, rows = self.delivery_info()
        if not names:
            return ""

        context_link = self.url + "/context_table/"
        rst_rows = self.add_context_links(1, rows, context_link, "table_")

        activity_link = self.url + "/recent_activity_query/?filename="
        rst_rows = self.add_context_links(2, rst_rows, activity_link, "actions_")

        table = crds_rst.CrdsTable(
            self.title("Deliveries"), names, rst_rows, format=("+","="))
        return table.to_rst() + "\n"

# ==============================================================================

def get_delivery_status(since_date):
    """Return a list of delivery status dictionaries for deliveries which occurred
    after `self.since_date`.
    """
    return api.S.get_delivery_status(since_date)

# ==============================================================================

def main(observatory, usecase, url, days_back):
    status = ServerStatus(observatory, usecase, url, int(days_back))
    print(status.to_rst())

if __name__ == "__main__":
    main(*sys.argv[1:])

