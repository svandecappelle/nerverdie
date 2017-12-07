"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src import utils

import src.console.watching.formatters as formatters
from src.console.watching.formatters import FormatterPrinter

from src.console.metric import Metric

class Formatter(FormatterPrinter):

    def __init__(self, window, screen):
        super(Formatter, self).__init__(window, screen)
        self.title = "Memory"

    def display(self):
        """Display infos"""
        value = self.value()
        self.reset()
        #self.print_line("test", highlight=True)
        virt = value.get('virtual')
        swap = value.get('swap')
        templ = "%-7s %10s %10s %10s %10s %10s %10s"
        self.print_line(templ % ('', 'total', 'used', 'free', 'shared', 'buffers', 'cache'))
        self.print_line(templ % (
            'Mem:',
            int(virt.total / 1024),
            int(virt.used / 1024),
            int(virt.free / 1024),
            int(getattr(virt, 'shared', 0) / 1024),
            int(getattr(virt, 'buffers', 0) / 1024),
            int(getattr(virt, 'cached', 0) / 1024)))
        self.print_line(templ % (
            'Swap:', int(swap.total / 1024),
            int(swap.used / 1024),
            int(swap.free / 1024),
            '',
            '',
            ''))
        used_percent = virt.used * 100 / virt.total
        self.print_percent("Used memory: ", used_percent)

    def value(self):
        return Metric().memory()