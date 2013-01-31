"""Minor extensions to JSON encoding/decoding to support serializing repeatable
results, particularly crds.refactor "actions".
"""

import json

class CrdsEncoder(json.JSONEncoder):
    """Convert non-standard objects to attr dicts to support template rendering.
    This works for simple objects with encode-able attributes.
    """
    def default(self, o):
        if not isinstance(o, (bool, int, float, list, tuple, dict, basestring)):
            o = dict(o.__dict__)
            for key, value in o.items():
                if isinstance(value, tuple):
                    o[key] = list(value)
        return o

def dumps(o):
    return json.dumps(o, cls=CrdsEncoder)

def loads(enc):
    o = json.loads(enc)
    if isinstance(o, dict):    # fix str --> unicode key decoding side effect.
        p = {}
        for key,val in o.items():
            if isinstance(key,basestring):
                p[str(key)] = val
            else:
                p[key] = val
        return p
    return o