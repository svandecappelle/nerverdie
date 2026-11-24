#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Network discovery agent: python agent.py -n 192.168.10.0/24"""

from server.network.scanner import NetworkDiscoverer, parse_args


def main():
    args = parse_args()
    NetworkDiscoverer().discover_all(args.network, args.timeout)


if __name__ == '__main__':
    main()
