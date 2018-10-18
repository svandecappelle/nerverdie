#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Console monit menu"""
from server.console import console


def main():
    try:
        console.main()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == '__main__':
    main()
