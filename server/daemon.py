#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
from datetime import date
from multiprocessing import Process
import schedule
import time

import psutil

from server.console import metric
from server.models.base import db
from server.models.metrics import Cpu, CpuCore, Measure
from server.storage import retention


class Daemon():

    def __init__(self):
        """Constructor"""
        # Previous network counters, to store a throughput instead of totals.
        self._network = None

    def measures(self):
        """Memory used and network throughput (bytes/s) since the previous run."""
        values = {
            'memory.used': psutil.virtual_memory().used,
            'memory.swap': psutil.swap_memory().used,
        }
        now = time.monotonic()
        received, sent = metric.network_totals()
        if self._network:
            then, previous_received, previous_sent = self._network
            elapsed = now - then
            # Counters can restart (interface reset): skip that sample.
            if elapsed > 0 and received >= previous_received and sent >= previous_sent:
                values['network.incoming'] = (received - previous_received) / elapsed
                values['network.outgoing'] = (sent - previous_sent) / elapsed
        self._network = (now, received, sent)
        return values

    def job(self):
        """Collecting job"""
        print("Collect monitor data...")
        metric_cpu = metric.Metric().cpu_load()[0]
        date = metric_cpu['date']
        cpus_load = {k: v for k, v in metric_cpu.items() if k.startswith('cpu')}
        measures = self.measures()
        with db.atomic():
            cpu = Cpu.create(time=date)
            CpuCore.insert_many(
                [{'cpu': cpu, 'name': key, 'load': value} for key, value in cpus_load.items()]
            ).execute()
            Measure.insert_many(
                [{'sample': cpu, 'name': key, 'value': value} for key, value in measures.items()]
            ).execute()
        # Slide the data: drop the oldest samples when the size limit is reached.
        deleted = retention.enforce_limit()
        if deleted:
            print("Database size limit reached: deleted %d old samples" % deleted)
        print("-"*32)

    def check(self):
        """Check todays datas"""
        today = date.today()

        print('storage datas:')
        for cpu in CpuCore.select():
            print(cpu.name)

        cpucores = CpuCore.select(
                CpuCore, Cpu
            ).join(Cpu).where(
                Cpu.time > today
            ).order_by(
                Cpu.time.asc(),
                CpuCore.name.asc()
            )
        for cpucore_metric in cpucores:
            print(cpucore_metric.cpu.time, cpucore_metric.name, cpucore_metric.load)
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
        # daemon=True: the collector stops with the server instead of
        # surviving it (or blocking its exit, as the loop never ends).
        daemon_processus = Process(target=self.loop, daemon=True)
        daemon_processus.start()
        return daemon_processus
