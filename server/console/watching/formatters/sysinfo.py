"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from server.console.watching.formatters import FormatterPrinter

from server.console.metric import Metric

class Formatter(FormatterPrinter):

    def __init__(self, window, screen):
        super(Formatter, self).__init__(window, screen)
        self.title = "System infos"

    def display(self):
        """format sysinfo"""
        self.reset()
        value = self.value()
        a_simple_row = """%s: %s"""
        for key in value.keys():
            self.print_line(a_simple_row % (key, value.get(key)))

    def value(self):
        return Metric().system_info()
