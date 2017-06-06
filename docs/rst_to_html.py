from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import sys

from docutils.core import publish_string

from crds import pysh

HEAD_ADDITIONS = """
<style>
{}
</style>
""".format(open("rst_to_html.css").read())

def rst_to_html(rst):
   html = publish_string(
       source=rst,
       settings_overrides={'file_insertion_enabled': 0, 'raw_enabled': 0},
       writer_name='html')
   html = html.replace("</head>", HEAD_ADDITIONS + "\n</head>")
   return html

if __name__ == "__main__":
   pysh.usage("<rst_file>", 1, 1, "Format a .rst file as .html to stdout.")
   rst = open(sys.argv[1]).read()
   html = rst_to_html(rst)
   print(html)
