from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
#: The version list
VERSION = (1, 0, 2)


def get_version():
    '''
    Converts the :attr:`VERSION` into a nice string
    '''
    if len(VERSION) > 3 and VERSION[3] not in ('final', ''):
        return '%s.%s.%s %s' % (VERSION[0], VERSION[1], VERSION[2], VERSION[3])
    else:
        return '%s.%s.%s' % (VERSION[0], VERSION[1], VERSION[2])


#: The version python displays
__version__ = get_version()
