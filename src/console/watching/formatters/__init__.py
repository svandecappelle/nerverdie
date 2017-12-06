"""Console formatters of monitoring"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import curses

class FormatterPrinter(object):
    """Printer using curses"""

    def __init__(self, window):
        self.window = window
        self.lineno = 0

    def print_line(self, line, highlight=False):
        """A thin wrapper around curses's addstr()."""
        try:
            if highlight:
                line += " " * (self.window.getmaxyx()[1] - len(line))
                self.window.addstr(self.lineno, 0, line, curses.A_REVERSE)
            else:
                self.window.addstr(self.lineno, 0, line, 0)
        except curses.error:
            self.lineno = 0
            self.window.refresh()
            raise
        else:
            self.lineno += 1

    def reset(self):
        self.lineno = 0
