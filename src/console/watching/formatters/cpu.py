"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.console.watching.formatters import FormatterPrinter

from src.console.metric import Metric

class Formatter(FormatterPrinter):

    def __init__(self, window, screen):
        super(Formatter, self).__init__(window, screen)
        self.title = "Cpu usage infos"

    def display(self):
        self.reset()
        value = self.value()
        proc_info = value.get('info')
        self.print_line("\tProcessor: %s" % proc_info)
        # self.print_line("\tarch: %s" % proc_info.get('arch'))

        cpu_use = value.get('usage')
        for cpu_num in range(0, (len(cpu_use))):
            perc = cpu_use[cpu_num]
            self.print_percent("cpu%-2s" % cpu_num, perc)

    def value(self):
        return Metric().cpu({
            'mode': 'simple'
        })
