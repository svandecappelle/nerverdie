#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
import logging
import scapy.config
import scapy.layers.l2
import scapy.route
import socket
import math
import errno
from multiprocessing import Process, Queue
import schedule
import time

from server.console import metric

class Daemon():

    def __init__(self):
        """Constructor"""


    def job(self):
        """Collecting job"""
        print("Collect monitor data...")
        print(metric.Metric().cpu_load())
        # TODO store datas
        print("-"*32)


    def loop(self):
        """Loop processus"""
        schedule.every(3).seconds.do(self.job)
        print("#"*17)
        print("# Agent started #")
        print("#"*17)
        print("")
        while True:
            schedule.run_pending()
            time.sleep(1)


    def start(self):
        """Daemon start method"""
        daemon_processus = Process(target=self.loop)
        daemon_processus.start()
