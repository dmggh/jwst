import sys

# ==================================================

import crds_rst

# ==================================================

def main(title, underline_char="^"):
    print(crds_rst.underline(title, underline_char))

# ==================================================

if __name__ == "__main__":
    main(*sys.argv[1:])




