"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

TEMPLATE = """press <ESC> to quit
%s:
%s
"""

def separation(width):
    """
    Separation token
    """
    return "-" * width

def progress(value, width):
    """
    Progress bar
    """
    return "#" * int(value * width / 100)

def sysinfo_format(value, height, width):
    """format sysinfo"""
    title = "System infos"
    a_simple_row = """
    %s: %s"""
    rows = ""
    for key in value.keys():
        rows += a_simple_row % (key, value.get(key))
    return TEMPLATE % (title, rows)

def cpu_format(value, height, width):
    """format cpu"""
    proc_info = value.get('info')
    informations = """\tProcessor: %s\n\tarch: %s\n""" % (proc_info.get('brand'), proc_info.get('arch'))
    usage = ""
    cpu_use = value.get('usage')
    for cpuunit in range(0, (len(cpu_use))):
        usage += """\tcpu%s: %s%%\n""" % (cpuunit + 1, cpu_use[cpuunit])
        usage += "%s\n" % progress(cpu_use[cpuunit], width)

    content = """%s\n%s\n%s""" % (separation(width), informations, usage)

    return TEMPLATE % ("Cpu usage infos", content)
