"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.console.watching.formatters import FormatterPrinter

from src.console.metric import Metric

class Formatter(FormatterPrinter):

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

    def value(self):
        return Metric().memory()