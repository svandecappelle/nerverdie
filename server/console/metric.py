"""Module metrics provides the metrics single functions to access system state"""
# -*- coding: utf-8 -*-

from enum import Enum

import time
import platform
import socket
import sys
import subprocess
import functools
import re
import threading

import cpuinfo
import psutil

from server import utils

af_map = {
    socket.AF_INET: 'IPv4',
    socket.AF_INET6: 'IPv6',
    psutil.AF_LINK: 'MAC',
}

# The CPU load is computed from psutil.cpu_times() deltas kept here, shared by
# every thread. psutil.cpu_percent() is not usable in the web server: its
# reference is kept per thread (psutil 7), and the waitress pool serves each
# request on any of its threads, so it mostly returned 0 %. The measure is also
# shared by close calls (the dashboard CPU tile and chart poll together), and
# renewed at most every CPU_MIN_INTERVAL seconds.
CPU_MIN_INTERVAL = 1.0
_cpu_lock = threading.Lock()
_cpu_measure = {'time': None, 'times': None, 'usage': None}


def _busy_percent(before, after):
    """Busy share of one core between two psutil.cpu_times() samples, in %."""
    idle = lambda times: times.idle + getattr(times, 'iowait', 0)  # noqa: E731
    total = sum(after) - sum(before)
    if total <= 0:
        return 0.0
    busy = total - (idle(after) - idle(before))
    return round(min(max(100.0 * busy / total, 0.0), 100.0), 1)


def cpu_percent_per_core():
    """Load of each core in %, over at least CPU_MIN_INTERVAL seconds."""
    with _cpu_lock:
        now = time.monotonic()
        if _cpu_measure['times'] is None:
            # The very first call has no reference: measure over a short interval.
            _cpu_measure['times'] = psutil.cpu_times(percpu=True)
            time.sleep(0.1)
        elif _cpu_measure['usage'] is not None and now - _cpu_measure['time'] < CPU_MIN_INTERVAL:
            return list(_cpu_measure['usage'])
        times = psutil.cpu_times(percpu=True)
        _cpu_measure['usage'] = [_busy_percent(before, after)
                                 for before, after in zip(_cpu_measure['times'], times, strict=False)]
        _cpu_measure['times'] = times
        _cpu_measure['time'] = time.monotonic()
        return list(_cpu_measure['usage'])


def network_totals():
    """Bytes received and sent since boot on all interfaces but loopback."""
    received = sent = 0
    for nic, counters in psutil.net_io_counters(pernic=True).items():
        if nic == 'lo' or nic.lower().startswith('loopback'):
            continue
        received += counters.bytes_recv
        sent += counters.bytes_sent
    return received, sent


@functools.lru_cache(maxsize=1)
def cpu_info():
    """Processor description. It does not change, and takes seconds to read."""
    return cpuinfo.get_cpu_info()


duplex_map = {
    psutil.NIC_DUPLEX_FULL: "full",
    psutil.NIC_DUPLEX_HALF: "half",
    psutil.NIC_DUPLEX_UNKNOWN: "?",
}


def get_processor_name():
    if platform.system() == "Windows":
        return platform.processor()
    elif platform.system() == "Darwin":
        output = subprocess.check_output(  # noqa: S603 (fixed command)
            ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"],
            universal_newlines=True)
        return output.strip()
    elif platform.system() == "Linux":
        with open("/proc/cpuinfo") as cpuinfo_file:
            for line in cpuinfo_file:
                if "model name" in line:
                    return re.sub(".*model name.*:", "", line, count=1).strip()
    return ""


def get_distribution():
    """Return (name, version, id) of the OS distribution when available.

    Replaces platform.linux_distribution(), removed in Python 3.8.
    """
    try:
        release = platform.freedesktop_os_release()
    except OSError:
        return ("", "", "")
    return (release.get("NAME", ""), release.get("VERSION_ID", ""), release.get("ID", ""))


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
            usage = cpu_percent_per_core()
        else:
            usage = psutil.cpu_times(percpu=True)

        if opts.get('mode') == 'simple':
            info = get_processor_name()
        else:
            info = cpu_info()

        return {
            'info': info,
            'usage': usage
        }

    def cpu_load(self, opts=None):
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
            usage = cpu_percent_per_core()
        else:
            usage = psutil.cpu_times(percpu=True)

        i = 0
        output = {
            'date': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        for cpu_usage in usage:
            output['cpu%d' % i] = cpu_usage
            i += 1

        return [output]

    def memory(self, opts=None):
        """Get system memory usage"""
        return {
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'virtual': psutil.virtual_memory(),
            'swap': psutil.swap_memory()
        }

    def memory_loads(self, opts=None):
        """Get system memory usage"""
        return [{
            'date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'virtual': psutil.virtual_memory()[3],
            'swap': psutil.swap_memory()[1]
        }]

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
        # Not provided by psutil on Windows and macOS.
        if not hasattr(psutil, 'sensors_temperatures'):
            return {}
        return psutil.sensors_temperatures()

    def system_info(self, opts=None):
        """Get system information"""
        return {
            'hostname': socket.gethostname(),
            'fqdn': socket.getfqdn(),
            'platform': {
                'distribution': get_distribution(),
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
                # print("    %-4s" % af_map.get(addr.family, addr.family))
                # print(" address   : %s" % addr.address)
                current = {
                    'name': "%-4s" % af_map.get(addr.family, addr.family),
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
