#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import importlib
import re

from src.server import APP as app
from src.server import flaskrun

API_LOCATION="src.web.api"

from src.settings.logger import LoggerConfigurator

class Starter(object):
    """ Monitoring application entry point"""
    def __init__(self):
        self.logger = logging.getLogger('Neverdie')
        self.routing()

    def routing(self):
        """Routing application"""
        self.logger.info("importing routes %s" % API_LOCATION)
        routes_location = re.sub(r'\.', r'/', API_LOCATION)
        self.logger.info(routes_location)
        for module in os.listdir(routes_location):
            if re.match(r'.*\.py$', module) and module != '__init__.py':
                route_file = re.sub(r'\.py', r'', module)
                self.logger.info("importing routes: %s" % route_file)
                route_module = importlib.import_module("%s.%s" % (API_LOCATION, route_file))
       
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