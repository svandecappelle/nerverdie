# -*- coding: utf-8 -*-

import ast

from datetime import date, datetime, time, timedelta


from server.console.metric import Metric
from server.models.metrics import Cpu, CpuCore

from flask import jsonify

import numpy as np


def modularRange(start, end, step, mod):
  return (i % mod for i in range(start, end + 1 + (0 if end >= start else mod), step))

def add_delta(date, seconds):
  return date + timedelta(seconds = seconds)

def arrays_of_times(start, end, step):
  diff = end - start
  startSec = (start.hour * 60 + start.minute) * 60 + start.second # Convert to seconds
  endSec = startSec + (diff.days * 24 * 3600) + diff.seconds
  return np.array([add_delta(start, secs - startSec) for secs in modularRange(startSec, endSec, step, 24 * 60 * 60 * 365)])


#start = datetime.now()
#end = start + timedelta(hours=1)
#end_in_ten_days = datetime.now() + timedelta(days=4)

#each_six_seconds = arrays_of_times(start, end, 6) 
#print(each_six_seconds)
#print(len(each_six_seconds))

#each_ten_minutes = arrays_of_times(start, end, 10 * 60)
#print(each_ten_minutes)
#print(len(each_ten_minutes))

#each_two_days = arrays_of_times(start, end_in_ten_days, 2 * 60 * 60 * 24)
#print(each_two_days)
#print(len(each_two_days))

def map_dates(empty_filled, database_saved):
    def search(x):
        gen = (item for item in database_saved if item['date'] == x.strftime('%Y-%m-%d %H:%M:%S'))

        for item in gen:
            return item
        return {
            'date': x.strftime('%Y-%m-%d %H:%M:%S'),
            'cpu1': None,
            'cpu2': None,
            'cpu3': None,
            'cpu4': None
        }
    return list(map(search, empty_filled))

class History:
    def get(self, metric, tail=int(3600/3)):
        today = date.today()
        now = datetime.now()

        empty_datas = arrays_of_times(now - timedelta(hours=1), now , 3)

        cpucores = (CpuCore
          .select(CpuCore, Cpu)
          .join(Cpu)
          .where(Cpu.time > empty_datas[0])
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
        output = list(reversed(history[-tail:]))
        datas = map_dates(empty_datas, history)
        if history[0]['date'] != empty_datas[0].strftime('%Y-%m-%d %H:%M:%S'):
            history.append({
                'date': empty_datas[0].strftime('%Y-%m-%d %H:%M:%S'),
                'cpu1': None,
                'cpu2': None,
                'cpu3': None,
                'cpu4': None
            })
        return history #-tail:
    