#!/usr/bin/env python
# -*- coding: utf-8 -*-

import schedule
import time

from server.console import metric
from server.daemon import NetworkDiscoverer

def job():
    print("Collect monitor data...")
    print(metric.Metric().cpu_load())
    print("-"*32)

#schedule.every(3).seconds.do(job)
#schedule.every(10).minutes.do(job)
#schedule.every().hour.do(job)
#schedule.every().day.at("10:30").do(job)
#schedule.every(5).to(10).minutes.do(job)
#schedule.every().monday.do(job)
#schedule.every().wednesday.at("13:15").do(job)

def main():
    discoverer = NetworkDiscoverer()
    discoverer.discover_all()
    #    print("#"*17)
    #    print("# Agent started #")
    #    print("#"*17)
    #    print("")
    #    while True:
    #        schedule.run_pending()
    #        time.sleep(1)

if __name__ == '__main__':
    main()