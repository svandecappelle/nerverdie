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
            print("defaults")
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

    def system_info(self, opt=None):
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