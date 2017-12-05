"""Module metrics provides the metrics single functions to access system state"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

import datetime
import os
import platform
import socket
import sys
import uuid

import cpuinfo
import psutil

af_map = {
    socket.AF_INET: 'IPv4',
    socket.AF_INET6: 'IPv6',
    psutil.AF_LINK: 'MAC',
}

duplex_map = {
    psutil.NIC_DUPLEX_FULL: "full",
    psutil.NIC_DUPLEX_HALF: "half",
    psutil.NIC_DUPLEX_UNKNOWN: "?",
}

def bytes2human(n):
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
    for s in reversed(symbols):
        if n >= prefix[s]:
            value = float(n) / prefix[s]
            return '%.2f%s' % (value, s)
    return '%.2fB' % (n)

class Format(Enum):
    """All metrics data types"""
    INTEGER = 0
    DOUBLE = 1
    PERCENT = 2

class Metric(object):
    """All metrics are accessible to call here"""

    def cpu(self, opts=None):
        """Entry of all cpu's units"""
        if opts is None:
            opts = {
                "format": Format.PERCENT
            }
        usage = None
        if opts['format'] == Format.PERCENT:
            usage = psutil.cpu_percent(percpu=True)
        else:
            usage = psutil.cpu_times(percpu=True)
        return {
            'info': cpuinfo.get_cpu_info(),
            'usage': usage
        }

    def memory(self, opts=None):
        """Get system memory usage"""
        return {
            'virtual': psutil.virtual_memory(),
            'swap': psutil.swap_memory()
        }

    def disk(self, opts=None):
        """Get system disk partitions & usage"""
        return {
            'partitions': psutil.disk_partitions(),
            'usage': psutil.disk_usage('/'),
            'ios': psutil.disk_io_counters(perdisk=True)
        }

    def uptime(self, opts=None):
        """Get system uptime"""
        return psutil.boot_time()

    def sensors(self, opts=None):
        """Get sensors details"""
        return psutil.sensors_temperatures()

    def system_info(self, opts=None):
        """Get system information"""
        return {
            'hostname': socket.gethostname(),
            'fqdn': socket.getfqdn(),
            'platform': {
                'distribution': platform.linux_distribution(),
                'sys': sys.platform,
                'platform': platform.platform()
            },
            'machine': platform.machine(),
            'node': platform.node(),
            'processor': platform.processor(),
            'os': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'nb_cpus': str(psutil.cpu_count()),
            'nb_physical_cpus': str(psutil.cpu_count(logical=False))
        }

    def network(self, opts=None):
        """Get network activity"""
        output = {}
        stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)
        for nic, addrs in psutil.net_if_addrs().items():
            network_interface = {}
            #print("%s:" % (nic))
            if nic in stats:
                st = stats[nic]
                #print("    stats          :")
                network_interface.update({'stats': {
                        'speed': st.speed,
                        'duplex': duplex_map[st.duplex],
                        'mtu': st.mtu,
                        'up': "yes" if st.isup else "no"
                    }
                })
                #print("speed=%sMB, duplex=%s, mtu=%s, up=%s" % (
                #    st.speed, duplex_map[st.duplex], st.mtu,
                #    "yes" if st.isup else "no"))
            if nic in io_counters:
                io = io_counters[nic]
                #print("    incoming       : ")
                network_interface.update({
                    'incoming': {
                        'bytes': bytes2human(io.bytes_recv),
                        'pkts': io.packets_recv,
                        'errs': io.errin,
                        'drops': io.dropin
                    }
                })
                #print("bytes=%s, pkts=%s, errs=%s, drops=%s" % (
                #    bytes2human(io.bytes_recv), io.packets_recv, io.errin,
                #    io.dropin))
                network_interface.update({
                    'outgoing': {
                        'bytes': bytes2human(io.bytes_sent),
                        'pkts': io.packets_sent,
                        'errs': io.errout,
                        'drops': io.dropout
                    }
                })
                #print("    outgoing       : ")
                #print("bytes=%s, pkts=%s, errs=%s, drops=%s" % (
                #    bytes2human(io.bytes_sent), io.packets_sent, io.errout,
                #    io.dropout))
            addresses = {}
            for addr in addrs:
                
                #print("    %-4s" % af_map.get(addr.family, addr.family))
                #print(" address   : %s" % addr.address)
                current = {
                    'name' : "%-4s" % af_map.get(addr.family, addr.family),
                    'address': addr.address
                }
                if addr.broadcast:
                    current.update({
                        'broadcast': addr.broadcast
                    })
                    #print("         broadcast : %s" % addr.broadcast)
                if addr.netmask:
                    current.update({
                        'broadcast': addr.netmask
                    })
                    #print("         netmask   : %s" % addr.netmask)
                if addr.ptp:
                    current.update({
                        'broadcast': addr.ptp
                    })
                    #print("      p2p       : %s" % addr.ptp)
                addresses.update({
                    "%-4s" % af_map.get(addr.family, addr.family): current
                })

            output.update({
                'addr': addresses
            })

            output.update({nic: network_interface})
            return output
