"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.console.watching.formatters import FormatterPrinter

from src.console.metric import Metric

class Formatter(FormatterPrinter):

    def display(self):
        self.reset()
        value = self.value()
        proc_info = value.get('info')
        self.print_line("Cpu usage infos")
        self.print_line("\tProcessor: %s" % proc_info)
        # self.print_line("\tarch: %s" % proc_info.get('arch'))

        cpu_use = value.get('usage')
        for cpu_num in range(0, (len(cpu_use))):
            perc = cpu_use[cpu_num]
            dashes, empty_dashes = self.get_dashes(perc)
            self.print_line("\tcpu%-2s [%s%s] %5s%%" % (cpu_num, dashes, empty_dashes,
                                              perc))
            #self.print_line("\tcpu%s: %s%% [%s%s]" % (cpuunit + 1, cpu_use[cpuunit]))
            #self.print_line("%s" % progress(cpu_use[cpuunit], self.window.width))

    def value(self):
        return Metric().cpu({
            'mode': 'simple'
        })
