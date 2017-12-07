"""Console formatters of monitoring"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import curses

STYLE = curses

START_CURSOR = 2


class FormatterPrinter(object):
    """Printer using curses"""

    def __init__(self, window, screen):
        self.window = window
        self.screen = screen
        self.lineno = -1
        self.cursor_x = START_CURSOR
        self.title = None
        y, x = self.window.getmaxyx()
        self.boxed = curses.newwin(y - 3, x - 3, 1, 1)
        self.boxed.scrollok(1)

    def print_line(self, line, highlight=False, style=None):
        """A thin wrapper around curses's addstr()."""
        if self.lineno == -1:
            self.lineno = 1
        self.lineno += 1
        self.cursor_x = START_CURSOR
        try:
            if style:
                line += " " * (self.window.getmaxyx()[1] - len(line) - START_CURSOR)
                self.screen.addstr(self.lineno, START_CURSOR, line, style)
            else:
                if highlight:
                    line += " " * (self.window.getmaxyx()[1] - len(line) - START_CURSOR - 10)
                    self.screen.addstr(self.lineno, START_CURSOR, line, curses.A_REVERSE)
                else:
                    self.screen.addstr(self.lineno, START_CURSOR, line, 0)
        except curses.error:
            self.lineno = START_CURSOR
            self.window.refresh()
            raise
    
    def print_inline(self, line, highlight=False, style=None):
        """A thin wrapper around curses's addstr()."""
        if self.lineno == -1:
            self.lineno = START_CURSOR
        if self.cursor_x == START_CURSOR:
            self.lineno += 1
        if self.cursor_x >= self.window.getmaxyx()[1]:
            self.cursor_x = START_CURSOR
            self.lineno += 1
        try:
            if style:
                self.window.addstr(self.lineno, self.cursor_x, line, style)
            else:
                if highlight:
                    self.window.addstr(self.lineno, self.cursor_x, line, curses.A_REVERSE)
                else:
                    self.window.addstr(self.lineno, self.cursor_x, line, 0)
            self.cursor_x += len(line)
        except curses.error:
            self.window.refresh()
            raise

    def reset(self):
        y, x = self.window.getmaxyx()
        subtitle = "[ <ESC> to return ]"
        self.window.addstr(0, x - len(subtitle) - 3, subtitle)
        self.lineno = 1
        if self.title:
            formatted_title = "[ %s ]" % self.title
            self.window.addstr(0, 3, formatted_title)
            self.lineno = 1

    def get_dashes(self, perc):
        dashes = " " * int((float(perc) / 10 * 4))
        empty_dashes = " " * (40 - len(dashes))
        return dashes, empty_dashes

    def print_percent(self, title, perc, carriage=True):
        dashes,blanks = self.get_dashes(perc)
        self.print_inline(title)
        self.print_inline("[")
        self.print_inline("%s" % dashes, style=STYLE.A_REVERSE)
        self.print_inline("%s] %s%%" % (blanks, perc))
        if carriage:
            self.cursor_x = START_CURSOR
        