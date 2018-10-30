#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
import logging
import scapy.config
import scapy.layers.l2
import scapy.route
import socket
import ast
import math
from datetime import date
import errno
from multiprocessing import Process, Queue
import schedule
import time

from server.console import metric
from server.storage.main import Datastore

storage = Datastore()

class Daemon():

    def __init__(self):
        """Constructor"""


    def job(self):
        """Collecting job"""
        print("Collect monitor data...")
        today = date.today()
        today_formatted = 'cpu_' + today.isoformat()
        metric_cpu = metric.Metric().cpu_load()[0]
        metric_time = today_formatted + '-' + str(time.time())
        storage.put(metric_time.encode(), str(metric_cpu).encode())
        # print(storage.get(today_formatted.encode()))
        # TODO store datas
        print("-"*32)


    def check(self):
        today = date.today()
        today_formatted = 'cpu_%s-' % today.isoformat()
        
        storage = Datastore()
        print('storage datas:')
        for key, value in storage.iterator(start = today_formatted):
            print(key)
        print('end')


    def loop(self):
        """Loop processus"""
        schedule.every(3).seconds.do(self.job)
        # schedule.every(1).seconds.do(self.check)
        
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
