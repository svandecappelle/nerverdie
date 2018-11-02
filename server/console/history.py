# -*- coding: utf-8 -*-

import ast

from datetime import date


from server.console.metric import Metric
from server.models.metrics import Cpu, CpuCore

from flask import jsonify


class History:
    def get(self, metric, tail=int(3600/3)):
        today = date.today()
        today_formatted = '%s_%s' % (metric, today.isoformat())

        cpucores = (CpuCore
          .select(CpuCore, Cpu)
          .join(Cpu)
          .where(Cpu.time > today)
          .order_by(Cpu.time.asc(), CpuCore.name.asc()))
        history = []
        metric_entry = None
        for cpucore_metric in cpucores:
            if metric_entry and metric_entry['date'] == str(cpucore_metric.cpu.time):
                metric_entry[cpucore_metric.name] = float(cpucore_metric.load)
            elif metric_entry and metric_entry['date'] != str(cpucore_metric.cpu.time):
                metric_entry[cpucore_metric.name] = float(cpucore_metric.load)
                history.append(metric_entry)
                metric_entry = None
            else:
                metric_entry = {
                    'date': str(cpucore_metric.cpu.time),
                    cpucore_metric.name: float(cpucore_metric.load)
                }
        return list(reversed(history[-tail:])) #-tail:
    