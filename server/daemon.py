#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function
from datetime import date
from multiprocessing import Process
import schedule
import time

from server.console import metric
from server.models.metrics import Cpu, CpuCore


class Daemon():

    def __init__(self):
        """Constructor"""

    def job(self):
        """Collecting job"""
        print("Collect monitor data...")
        metric_cpu = metric.Metric().cpu_load()[0]
        date = metric_cpu['date']
        cpus_load = {k: v for k, v in metric_cpu.items() if k.startswith('cpu')}
        cpu = Cpu.create(time=date)
        for (key, value) in cpus_load.items():
            cpucore = CpuCore(cpu=cpu, load=value, name=key)
            cpucore.save()
        print("-"*32)

    def check(self):
        """Check todays datas"""
        today = date.today()
        today_formatted = 'cpu_%s-' % today.isoformat()

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
        daemon_processus = Process(target=self.loop)
        daemon_processus.start()
