#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib

from server.application import APP as app
from server.application import flaskrun
from server.settings.logger import LoggerConfigurator

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROUTES_FOLDERS = [os.path.join("server", "web")]

def walk(directory, only_regular_files=True):
    out = []
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            out.append(os.path.join(root, name))
        if not only_regular_files:
            for name in dirs:
                out.append(os.path.join(root, name))
    return out

class Starter(object):
    """ Monitoring application entry point"""
    def __init__(self):
        self.logger = logging.getLogger('Neverdie')
        self.routing()

    def routing(self):
        """Routing application"""
        for route_folder in ROUTES_FOLDERS:
            modules = walk(os.path.join(BASE_DIR, route_folder))
            for module in modules:
                if module.endswith('.py') and os.path.basename(module) != '__init__.py':
                    # Build the dotted module name from the path, whatever
                    # the OS path separator is ('\\' on Windows).
                    relative = os.path.relpath(module, BASE_DIR)
                    route_file = os.path.splitext(relative)[0].replace(os.sep, '.')
                    self.logger.info("importing routes: %s", route_file)
                    importlib.import_module(route_file)

    def launch(self):
        """Launch api server"""
        self.logger.info("Starting server")
        flaskrun(app)

    def status(self):
        """Check starting status"""

    def stop(self):
        """Stop api server"""

def main():
    """Enty point"""
    logger_configurator = LoggerConfigurator()
    logger_configurator.configure()
    starter = Starter()
    starter.launch()

if __name__ == '__main__':
    main()
