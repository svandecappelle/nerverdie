"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.console.watching.formatters import FormatterPrinter

from src.console.metric import Metric

class Formatter(FormatterPrinter):

    def display(self):
        """format sysinfo"""
        self.reset()
        value = self.value()
        title = "System infos"
        a_simple_row = """%s: %s"""
        self.print_line("press <ESC> to quit")
        self.print_line(title)
        #keys = 
        for key in value.keys():
            self.print_line(a_simple_row % (key, value.get(key)))

    def value(self):
        return Metric().system_info()
