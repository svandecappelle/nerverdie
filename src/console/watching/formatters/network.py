"""Watching information until <ESC> is pressed"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from src.console.watching.formatters import FormatterPrinter

from src.console.metric import Metric

class Formatter(FormatterPrinter):

    def __init__(self, window, screen):
        super(Formatter, self).__init__(window, screen)
        self.title = "Network monitor"

    def display(self):
        """
        network monitor
        """
        self.reset()
        value = self.value()
        for interface in value:
            self.print_line("%s: " % interface, True)
            properties = value.get(interface)
            
            incoming = properties.get('incoming')
            outgoing = properties.get('outgoing')
            stats = properties.get('stats')
            addresses = properties.get('addr')
            
            self.print_line("\tincoming:")
            self.print_line("\t\tbytes: %s, drops: %s, errs: %s, pkts: %s" % (incoming.get('bytes'), incoming.get('drops'), incoming.get('errs'), incoming.get('pkts')))

            self.print_line("\toutgoing")
            self.print_line("\t\tbytes: %s, drops: %s, errs: %s, pkts: %s" % (outgoing.get('bytes'), outgoing.get('drops'), outgoing.get('errs'), outgoing.get('pkts')))

            self.print_line("\tstats")
            self.print_line("\t\tspeed: %s, duplex: %s, mtu: %s, up: %s" % (stats.get('speed'), stats.get('duplex'), stats.get('mtu'), stats.get('up')))

            for addr in addresses:
                self.print_line("\tAddr %s" % addr)
                properties = addresses.get(addr)

                self.print_line("\t\taddress   : %s" % properties.get('address'))
                if properties.get('broadcast'):
                    self.print_line("\t\tbroadcast : %s" % properties.get('broadcast'))
                if properties.get('netmask'):
                    self.print_line("\t\tnetmask   : %s" % properties.get('netmask'))
                if properties.get('ptp'):
                    self.print_line("\t\tp2p       : %s" % properties.get('ptp'))


    def value(self):
        return Metric().network()