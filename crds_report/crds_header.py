import sys

# ==================================================

import crds_rst

# ==================================================

def header(DATE):
    title = f"""CRDS Weekly Status {DATE}"""
    return crds_rst.underline(title, "^")

def main(date):
    print(header(date))

# ==================================================

if __name__ == "__main__":
    main(sys.argv[1])




