"""Module utility provides the utilities function"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

def bytes2human(value_to_format, precise=False):
    """
    >>> bytes2human(10000)
    '9.8 K'
    >>> bytes2human(100001221)
    '95.4 M'
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    for i, s in enumerate(symbols):
        prefix[s] = 1 << (i + 1) * 10
    for i, s in enumerate(reversed(symbols)):
        if value_to_format >= prefix[s]:
            value = float(value_to_format) / prefix[s]
            return '%.2f%s' % (value, s)
    return '%.2fB' % (value_to_format)
