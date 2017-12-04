#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum
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
        if opts['format'] == Format.PERCENT:
            return psutil.cpu_percent(percpu=True)
        else:
            return psutil.cpu_times(percpu=True)

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