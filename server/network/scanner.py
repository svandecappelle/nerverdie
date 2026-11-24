# Christoph Franke
# mail@cfranke.org
# 12.02.2019
from functools import reduce

from netaddr import IPSet
import socket
import subprocess
import argparse
import signal
import sys


scanning_ports = {
    'ftp': {
        'default_port': 21
    },
    'ssh': {
        'default_port': 22
    },
    'http': {
        'default_port': 80
    },
    'https': {
        'default_port': 443
    },
    'smb': {
        'default_port': 445
    },
    'rdp': {
        'default_port': 3389
    },
    'nerverdie': {
        'default_port': 5000
    }
}


# Catch SIGIN STRG+C
def signal_handler(sig, frame):
        print('Scan stopped.')
        sys.exit(0)


class NetworkDiscoverer:
    """
    """

    # Portscan
    def checkPort(self, ip, port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.3)
            s.connect((ip, port))
            s.shutdown(1)
            return True
        except Exception:
            return False

    # Reverse Lookup
    def lookup(self, addr):
        try:
            data = socket.gethostbyaddr(str(addr))
            host = repr(data[0])
            host = str(host)
            host = host.strip("'")
            return host
        except Exception:
            return "NA"

    def discover_all(self, network, timeout='0.2'):
        """Ping and port-scan every host of `network` (e.g. '192.168.10.0/24').

        Only scan networks you are responsible for. Returns {ip: ports_status}.
        """
        signal.signal(signal.SIGINT, signal_handler)
        results = {}

        # Color Output
        col_green = "\033[0;32m"
        col_red = "\033[1;31m"
        col_norm = "\033[0m"
        # Print Header
        print("IP, STATUS, HOSTNAME, ftp, ssh, http, https, smb, rdp")

        # Loop through Subnet and try to ping and portscan host
        for ip in IPSet([network]):
            try:
                subprocess.check_output([  # noqa: S603, S607 (no shell, fixed command)
                        'ping',
                        '-c',
                        '3',
                        "-W",
                        "1",
                        "-i",
                        str(timeout),
                        str(ip)
                    ],
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                online = False
                hostname = str(self.lookup(str(ip)))
                ports_status = dict(map(lambda x: (x, False), scanning_ports.keys()))
                for (port, properties) in scanning_ports.items():
                    if (self.checkPort(str(ip), properties.get('default_port'))):
                        online = True
                        ports_status[port] = True
                if online:
                    print('{}, {}, {}, {}'.format(
                        str(ip),
                        col_green + "ONLINE" + col_norm,
                        hostname,
                        str(reduce(
                            lambda x, str: str + ', ' + x,
                            map(
                                lambda x: '{}'.format(ports_status[x]),
                                ports_status.keys()
                            )
                        ))
                    ))
                else:
                    print(str(ip) + ", " + col_red + "OFFLINE" + col_norm + ", NA")
                results[str(ip)] = ports_status

            # Catch Error
            except subprocess.CalledProcessError:
                print(str(ip) + ", " + col_red + "OFFLINE" + col_norm + ", NA")
        return results


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Subnet Scanner')
    parser.add_argument('-n', '--network', help='e.g. 192.168.10.0/24', required=True)
    parser.add_argument('-t', '--timeout', help='timeout in seconds', default='0.2')
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    NetworkDiscoverer().discover_all(args.network, args.timeout)
