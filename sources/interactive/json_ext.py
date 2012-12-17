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

class CrdsDecoder(json.JSONDecoder):
    pass   # stub this for now and just return the object dict


def dumps(o):
    return json.dumps(o, cls=CrdsEncoder)

def loads(enc):
    return json.loads(enc, cls=CrdsDecoder)
