#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
import cpuinfo
import datetime
import os
import platform
import psutil
import socket
import sys
import uuid

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
        return { 
            'virtual': psutil.virtual_memory(),
            'swap': psutil.swap_memory()
        }

    def disk(self, opts=None):
        return {
            'partitions': psutil.disk_partitions(),
            'usage': psutil.disk_usage('/'),
            'ios': psutil.disk_io_counters(perdisk=True)
        }
    
    def uptime(self, opts=None):
        return psutil.boot_time()

    def sensors(self, opts=None):
        return psutil.sensors_temperatures()

    def system_info(self, opt=None):
        return {
            'Name': socket.gethostname(),
            'FQDN': socket.getfqdn(),
            'System Platform': sys.platform,
            'Machine': platform.machine(),
            'Node': platform.node(),
            'Platform': platform.platform(),
            'Pocessor': platform.processor(),
            'System OS': platform.system(),
            'Release': platform.release(),
            'Version': platform.version(),
            'Number of CPUs': str(psutil.cpu_count()),
            'Number of Physical CPUs': str(psutil.cpu_count(logical=False))
        }