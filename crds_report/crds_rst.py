import numpy as np

# =======================================================================

class CrdsTableRow(tuple):
    """
    >>> row = CrdsTableRow(("Default Context", "hst_0449.pmap"))
    >>> row.resolve()
    ('Default Context', 'hst_0449.pmap')
    
    >>> row = CrdsTableRow(("Default Context", lambda: "hst_0448.pmap"))
    >>> row.resolve()
    ('Default Context', 'hst_0448.pmap')
    """
    def resolve(self):
        resolved = []
        for field in self:
            if isinstance(field, str):
                resolved.append(field)
            else:
                resolved.append(field())
        return tuple(resolved)

# =======================================================================

class CrdsTable(object):
    """
    >>> table = CrdsTable(
    ...     "This is the title", ("Location", "Context"),
    ...      [("Pipeline", "hst_0449.pmap"),
    ...       ("Onsite User", lambda: "hst_0448.pmap"),
    ...      ])
    >>> print(table.to_rst())
    This is the title
    -----------------
    =========== =============
    Location    Context       
    =========== =============
    Pipeline    hst_0449.pmap 
    Onsite User hst_0448.pmap 
    =========== =============
    <BLANKLINE>
    """
    def __init__(self, title, name_row, data_rows, format=("-","=")):
        self.title = title
        self.rows = []
        self._format = format
        self._name_row = CrdsTableRow(name_row)
        self._data_rows = [CrdsTableRow(row) for row in data_rows]

    def __str__(self):
        return self.to_rst()

    def to_rst(self):
        rst = ""
        if self.title:
            rst += self.title + "\n" + self._format[0]*len(self.title) + "\n"
        rst += self.table_to_rst()
        return rst

    def resolve_rows(self):
        rows = [self._name_row.resolve()]
        rows += [row.resolve() for row in self._data_rows]
        return rows

    def table_to_rst(self):
        if not self.rows:
            self.rows = self.resolve_rows()
        maxes = max_item_lengths(self.rows)
        self.underline_row = table_underline(maxes, self._format[1])
        self.justified = justify_rows(maxes, self.rows)
        rst_rows = [
            self.underline_row,
            self.justified[0],
            self.underline_row
            ]
        rst_rows += self.justified[1:]
        rst_rows += [self.underline_row]
        rst = "\n".join(rst_rows) + "\n"
        return rst

# =======================================================================

def max_item_lengths(rows):
    """
    >>> rows = [
    ...   ("This is an item",  "Shorter", "Longer item"),
    ...   ("This is 2",  "Shorter 2", "Longer item 2"),
    ... ]
    >>> max_item_lengths(rows)
    [15, 9, 13]
    """
    lengths = [ [ len(item) for item in row] for row in rows]
    a = np.array(lengths)
    a = a.transpose()
    maxes = [ max(row) for row in a ]
    return maxes

def table_underline(maxes, underline='='):
    """
    >>> print(table_underline([2,5,3]))
    == ===== ===
    """
    underlines = [underline*maxlen for maxlen in maxes]
    return " ".join(underlines)

def justify_rows(maxes, rows):
    justified = []
    for row in rows:
        items = []
        for i, item in enumerate(row):
            item += " "*(maxes[i]-len(item)+1)
            items.append(item)
        justified.append("".join(items))
    return justified

def underline(line, char="-"):
    return line + "\n" + char*len(line) + "\n"

# =======================================================================

def link_use_rst(name):
    return "`" + name + "`_"

def unlink_rst(name):
    return name[1:-2]

def link_def_rst(name, url):
    if not url.endswith("/") and "?" not in url:
        url += "/"
    return ".. _`" + name + "`: " + url

# =======================================================================

def test():
    import doctest, crds_rst
    return doctest.testmod(crds_rst)

if __name__ == "__main__":
    print(test())

