"""Minor extensions to JSON encoding/decoding to support serializing repeatable
results, particularly crds.refactor "actions".
"""

import json

class CrdsEncoder(json.JSONEncoder):
    """Convert non-standard objects to attr dicts to support template rendering.
    This works for simple objects with encode-able attributes.
    """
    def default(self, obj):
        if not isinstance(obj, (bool, int, float, list, tuple, dict, basestring)):
            obj = dict(obj.__dict__)
            for key, value in obj.items():
                if isinstance(value, tuple):
                    obj[key] = list(value)
        return obj

def dumps(obj):
    """Render obj as a json string using CrdsEncoder."""
    return json.dumps(obj, cls=CrdsEncoder)

def loads(enc):
    """Create a Python object from a json string.  Hack away unicode keys."""
    obj = json.loads(enc)
    if isinstance(obj, dict):    # fix str --> unicode key decoding side effect.
        pobj = {}
        for key, val in obj.items():
            if isinstance(val, basestring):
                val = str(val)
            if isinstance(key, basestring):
                pobj[str(key)] = val
            else:
                pobj[key] = val
        return pobj
    return obj