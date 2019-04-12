#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from logging.handlers import RotatingFileHandler


class LoggerConfigurator:
    """Junxia default system logger configurator"""

    def __init__(self):
        """Init logging system handlers"""

    def configure(self):
        # création de l'objet logger qui va nous servir à écrire dans les logs
        logger = logging.getLogger()
        # on met le niveau du logger à DEBUG, comme ça il écrit tout
        logger.setLevel(logging.INFO)

        # création d'un formateur qui va ajouter le temps, le niveau
        # de chaque message quand on écrira un message dans le log
        FORMAT = '%(asctime)s :: %(levelname)s :: %(message)s'
        formatter = logging.Formatter(FORMAT)
        logging.basicConfig(format=FORMAT)

        # création d'un handler qui va rediriger une écriture du log vers
        # un fichier en mode 'append', avec 1 backup et une taille max de 1Mo
        file_handler = RotatingFileHandler('activity.log', 'a', 1000000, 1)
        # on lui met le niveau sur DEBUG, on lui dit qu'il doit utiliser le formateur
        # créé précédement et on ajoute ce handler au logger
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # création d'un second handler qui va rediriger chaque écriture de log
        # sur la console
        # steam_handler = logging.StreamHandler()
        # steam_handler.setLevel(logging.DEBUG)
        # logger.addHandler(steam_handler)
