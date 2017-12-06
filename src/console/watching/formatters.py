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
    return u'\u4e00' * (width / 2)

def progress(value, width):
    """
    Progress bar
    """
    return u'\u4e00' * int(value * (width / 2) / 100)

def sysinfo(value, height, width):
    """format sysinfo"""
    title = "System infos"
    a_simple_row = """
    %s: %s"""
    rows = ""
    for key in value.keys():
        rows += a_simple_row % (key, value.get(key))
    return TEMPLATE % (title, rows)

def cpu(value, height, width):
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

def network(value, height, width):
    """
    network monitor
    """
    output = ""
    for interface in value:
        output += "\n%s: " % interface
        properties = value.get(interface)
        
        incoming = properties.get('incoming')
        outgoing = properties.get('outgoing')
        stats = properties.get('stats')
        addresses = properties.get('addr')
        
        output += "\n\tincoming:\n"
        output += "\t\tbytes: %s, drops: %s, errs: %s, pkts: %s" % (incoming.get('bytes'), incoming.get('drops'), incoming.get('errs'), incoming.get('pkts'))

        output += "\n\toutgoing\n"
        output += "\t\tbytes: %s, drops: %s, errs: %s, pkts: %s" % (outgoing.get('bytes'), outgoing.get('drops'), outgoing.get('errs'), outgoing.get('pkts'))

        output += "\n\tstats\n"
        output += "\t\tspeed: %s, duplex: %s, mtu: %s, up: %s" % (stats.get('speed'), stats.get('duplex'), stats.get('mtu'), stats.get('up'))

        for addr in addresses:
            output += "\n\tAddr %s" % addr
            properties = addresses.get(addr)

            output += "\n\t\taddress   : %s" % properties.get('address')
            if properties.get('broadcast'):
                output += "\n\t\tbroadcast : %s" % properties.get('broadcast')
            if properties.get('netmask'):
                output += "\n\t\tnetmask   : %s" % properties.get('netmask')
            if properties.get('ptp'):
                output += "\n\t\tp2p       : %s" % properties.get('ptp')

    return output

def memory(value, height, width):
    """Format memory"""
    return 'Memory'