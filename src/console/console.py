"""Console call menu"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
import curses
import os
import traceback

from src.console.watching import watch

MONIT = watch.Printer()

class CursedMenu(object):
    """A class which abstracts the horrors of building a curses-based menu system"""

    def __init__(self):
        """Initialization"""
        self.subtitle = None
        self.title = None
        self.selected = 0
        self.options = None
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        curses.start_color()
        self.screen.keypad(1)

        # Highlighted and Normal line definitions
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.highlighted = curses.color_pair(1)
        self.normal = curses.A_NORMAL


    def show(self, options, title="Title", subtitle="Subtitle"):
        """Draws a menu with the given parameters"""
        self.set_options(options)
        self.title = title
        self.subtitle = subtitle
        self.selected = 0
        self.draw_menu()


    def set_options(self, options):
        """Validates that the last option is 'Exit'"""
        if not options.has_key(-1):
            options.update({
                0: {
                    'text': 'Exit',
                    'call': self.__exit__
                }
            })
        self.options = options


    def draw_menu(self):
        """Actually draws the menu and handles branching"""
        request = None
        try:
            while request is None or (request is not None and request.get('id') != 0):
                self.draw()
                request = self.get_user_input()
                self.handle_request(request)

        # Also calls __exit__, but adds traceback after
        except Exception as exception:
            self.__exit__()
            traceback.print_exc()


    def draw(self):
        """Draw the menu and lines"""
        self.screen.border(0)
        self.screen.addstr(2, 2, self.title, curses.A_STANDOUT) # Title for this menu
        self.screen.addstr(4, 2, self.subtitle, curses.A_BOLD) #Subtitle for this menu

        # Display all the menu items, showing the 'pos' item highlighted
        for index in range(len(self.options)):
            textstyle = self.normal
            if index == self.selected:
                textstyle = self.highlighted
            self.screen.addstr(5 + index, 4, "%d - %s" % (index + 1, self.options.get(index).get('text')), textstyle)

        self.screen.refresh()


    def get_user_input(self):
        """Gets the user's input and acts appropriately"""
        user_in = self.screen.getch() # Gets user input

        # Enter and Exit Keys are special cases
        if user_in == 10:
            return {
                'id': self.selected,
                'text' : self.options.get(self.selected).get('text')
            }
        if user_in == 27:
            return {
                'id': 0,
                'text': self.options.get(0).get('text')
            }

        # Increment or Decrement
        if user_in == curses.KEY_DOWN: # down arrow
            self.selected += 1
        if user_in == curses.KEY_UP: # up arrow
            self.selected -= 1
        self.selected = self.selected % len(self.options)

        if self.selected > len(self.options) + 1:
            self.selected = 0

        return


    def handle_request(self, request):
        """This is where you do things with the request"""
        if request is None:
            return
        self.__exit__()
        self.options.get(request.get('id')).get('call')()

    def __exit__(self):
        curses.endwin()
        os.system('clear')

def main():
    """Console main function"""
    menu = CursedMenu()
    menu.show({
        1: {
            'text': 'System informations',
            'call': MONIT.sys_info
        },
        2:  {
            'text': 'monitor cpu',
            'call': MONIT.monit_cpu
        },
        3:  {
            'text': 'monitor memory',
            'call': MONIT.monit_memory
        },
    }, title='Main menu', subtitle='select what to monitor')

if __name__ == '__main__':
    main()
