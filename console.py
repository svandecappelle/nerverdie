"""Console monit menu"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from src.console import console


def main():
    try:
        console.main()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == '__main__':
    main()
