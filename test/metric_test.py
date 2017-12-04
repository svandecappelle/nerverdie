#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest2 as unittest
from src.console.metric import Metric as metric

class TestMetric(unittest.TestCase):
    """Metric getting tests unit"""

    def cpu(self):
        """Test if cpu is reachable"""
        metrics_instance = metric()
        metrics_instance.cpu()

if __name__ == '__main__':
    unittest.main()
