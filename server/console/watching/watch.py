"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals # convenient for Python 2

# Python 3 compliance
try:
    import thread
except ImportError:
    import _thread as thread

import os
import time
import curses
import atexit

import sys
import termios
import fcntl


from server.console.watching.formatters import sysinfo
from server.console.watching.formatters import memory
from server.console.watching.formatters import network
from server.console.watching.formatters import cpu



MAX_FPS = 1
time_per_frame = 1. / MAX_FPS


class _Getch:
    """Gets a single character from standard input.  Does not echo to the
screen."""
    def __init__(self):
        try:
            self.impl = _GetchWindows()
        except ImportError:
            self.impl = _GetchUnix()

    def __call__(self): return self.impl()


class _GetchUnix:
    def __init__(self):
        import tty, sys

    def __call__(self):
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch


class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

getch = _Getch()

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
        self.stdscr = curses.initscr()
        self.formatter = watcher(self.win, self.stdscr)
        atexit.register(self.tear_down)
        curses.endwin()

    def tear_down(self):
        self.win.keypad(0)
        self.win.refresh()
        curses.nocbreak()
        curses.echo()
        curses.endwin()

    def poll(self, interval):
        """nothing"""
        # sleep some time
        time.sleep(interval)

    def watch(self, interval=1):
        
        def loop(a_list):
            time.sleep(1)
            char = getch() 
            a_list.append(True)
            #print("'%s'" % char)
            #while not getch() != '':
            #    a_list.append(True)
        
        cur_interval = 0
        a_list = []
        thread.start_new_thread(loop, (a_list,))
        while not a_list:
            self.poll(cur_interval)
            self.display()
            cur_interval = interval

        self.win.erase()
        curses.endwin()

    def display(self):
        self.refresh_window()

    def refresh_window(self):
        """Print results on screen by using curses."""
        #curses.endwin()
        self.win.erase()
        self.stdscr.border(0)
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
