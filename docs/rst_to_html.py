from __future__ import print_function

import sys

from docutils.core import publish_string

from crds import pysh

def rst_to_html(rst):
   return publish_string(
       source=rst,
       settings_overrides={'file_insertion_enabled': 0, 'raw_enabled': 0},
       writer_name='html')

if __name__ == "__main__":
   pysh.usage("<rst_file>", 1, 1, "Format a .rst file as .html to stdout.")
   rst = open(sys.argv[1]).read()
   print(rst_to_html(rst))
