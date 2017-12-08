"""Module metrics provides the metrics single functions to access system state"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum

import time
import os
import platform
import socket
import sys
import uuid
import subprocess
import re

import cpuinfo
import psutil

from src import utils

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

def get_processor_name():
    if platform.system() == "Windows":
        return platform.processor()
    elif platform.system() == "Darwin":
        os.environ['PATH'] = os.environ['PATH'] + os.pathsep + '/usr/sbin'
        command ="sysctl -n machdep.cpu.brand_string"
        return subprocess.check_output(command).strip()
    elif platform.system() == "Linux":
        command = "cat /proc/cpuinfo"
        all_info = subprocess.check_output(command, shell=True).strip()
        for line in iter(all_info.splitlines()):
            if "model name" in str(line):
                return re.sub( ".*model name.*:", "", str(line),1)
    return ""


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
            opts = {}
        if 'format' not in opts: 
            opts.update({
                "format": Format.PERCENT
            })
        if 'mode' not in opts:
            opts.update({
                "mode": 'complex'
            })
        usage = None
        if opts['format'] == Format.PERCENT:
            usage = psutil.cpu_percent(percpu=True)
        else:
            usage = psutil.cpu_times(percpu=True)
        
        if opts.get('mode') == 'simple':
            info = get_processor_name()
        else:
            info = cpuinfo.get_cpu_info()

        return {
            'info': info,
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
        """Get system uptime miliseconds"""
        return (time.time() - psutil.boot_time()) * 1000

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
            if nic in stats:
                st = stats[nic]
                network_interface.update({'stats': {
                        'speed': st.speed,
                        'duplex': duplex_map[st.duplex],
                        'mtu': st.mtu,
                        'up': "yes" if st.isup else "no"
                    }
                })
            if nic in io_counters:
                io = io_counters[nic]
                network_interface.update({
                    'incoming': {
                        'bytes': utils.bytes2human(io.bytes_recv),
                        'pkts': io.packets_recv,
                        'errs': io.errin,
                        'drops': io.dropin
                    }
                })
                network_interface.update({
                    'outgoing': {
                        'bytes': utils.bytes2human(io.bytes_sent),
                        'pkts': io.packets_sent,
                        'errs': io.errout,
                        'drops': io.dropout
                    }
                })
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
                if addr.netmask:
                    current.update({
                        'broadcast': addr.netmask
                    })
                if addr.ptp:
                    current.update({
                        'broadcast': addr.ptp
                    })
                addresses.update({
                    "%-4s" % af_map.get(addr.family, addr.family): current
                })

                network_interface.update({
                    'addr': addresses
                })
            
            output.update({nic: network_interface})
        return output
