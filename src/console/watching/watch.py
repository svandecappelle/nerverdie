"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals # convenient for Python 2

import os
import random
import json
import itertools
import time

from curtsies import FullscreenWindow, Input, FSArray
from curtsies.fmtfuncs import red, bold, green, on_blue, yellow

from src.console.metric import Metric
import formatters

MAX_FPS = 1000
time_per_frame = 1. / MAX_FPS

class FrameWatcher(object):
    def __init__(self):
        self.render_times = []
        self.dt = .5

    def frame(self):
        self.render_times.append(time.time())

    def fps(self):
        now = time.time()
        while self.render_times and self.render_times[0] < now - self.dt:
            self.render_times.pop(0)
        return len(self.render_times) / max(self.dt, now - self.render_times[0] if self.render_times else self.dt)


class Printer(object):

    def __init__(self):
        """Initializer"""
        self.a = None
        self.window = None

    def printer(self, function, formatter):
        counter = FrameWatcher()
        with FullscreenWindow() as window:
            print('Press escape to exit')
            with Input() as input_generator:
                a = FSArray(window.height, window.width)
                c = None
                for framenum in itertools.count(0):
                    t0 = time.time()
                    while True:
                        t = time.time()

                        temp_c = input_generator.send(max(0, t - (t0 + time_per_frame)))
                        if temp_c is not None:
                            c = temp_c

                        if c is None:
                            pass
                        elif c == '<ESC>':
                            return
                        elif c == '<SPACE>':
                            a = FSArray(window.height, window.width)
                        else:
                            row = random.choice(range(window.height))
                            column = random.choice(range(window.width-len(c)))
                            a[row:row+1, column:column+len(c)] = [c]

                        c = None
                        if time_per_frame < t - t0:
                            break

                    #row = random.choice(range(window.height))
                    #column = random.choice(range(window.width))
                    row = 1
                    string = formatter(function(), window.height, window.width)
                    column = len(string)
                    #
                    # a[row:row+1, 0:column] = [string] #[random.choice(".,-'`~")]
                    window.render_to_terminal(window.array_from_text(string))

                    fps = 'FPS: %.1f' % counter.fps()
                    a[0:1, 0:len(fps)] = [fps]

                    #window.render_to_terminal(a)
                    counter.frame()

    def show(self, function, formatter):
        """Print on screen"""
        os.system('clear')
        self.printer(function, formatter)

    def sys_info(self):
        """View System infos"""
        self.show(Metric().system_info, formatters.sysinfo_format)

    def monit_cpu(self):
        """Monitor cpu"""
        self.show(Metric().cpu, formatters.cpu_format)

    def monit_network(self):
        """Monitor network"""
        self.show(Metric().network, formatters.network)

    def monit_memory(self):
        """Monitor memory"""