"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals # convenient for Python 2

import os
import time
import curses
import atexit

from src.console.watching.formatters import sysinfo
from src.console.watching.formatters import memory
from src.console.watching.formatters import network
from src.console.watching.formatters import cpu


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


class CursesPrinter(object):
    
    def __init__(self, watcher):
        self.win = curses.initscr()
        self.formatter = watcher(self.win)
        self.stdscr = curses.initscr()
        atexit.register(self.tear_down)
        curses.endwin()

    def tear_down(self):
        self.win.keypad(0)
        curses.nocbreak()
        curses.echo()
        curses.endwin()

    def poll(self, interval):
        # sleep some time
        time.sleep(interval)

    def watch(self, interval=1):
        cur_interval = 0
        while True:
            self.poll(cur_interval)
            self.display()
            cur_interval = interval
            #try:
            #    key = self.win.getkey()
            #except: # in no delay mode getkey raise and exeption if no key is press 
            #    key = None
            #if key == " ": # of we got a space then break
            #    break

        curses.endwin()

    def display(self):
        self.refresh_window()

    def refresh_window(self):
        """Print results on screen by using curses."""
        #curses.endwin()
        self.win.erase()
        self.formatter.display()
        self.win.refresh()

class Printer(object):

    def show(self, formatter, interval=1):
        """Print on screen"""
        #os.system('clear')
        printer = CursesPrinter(formatter)
        printer.watch(interval)

    def sys_info(self):
        """View System infos"""
        self.show(sysinfo.Formatter)
        
    def monit_cpu(self):
        """Monitor cpu"""
        self.show(cpu.Formatter, interval=1)

    def monit_network(self):
        """Monitor network"""
        self.show(network.Formatter)

    def monit_memory(self):
        """Monitor memory"""
        self.show(memory.Formatter)
