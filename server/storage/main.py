#!/usr/bin/env python
# -*- coding: utf-8 -*-

import plyvel

DB_LOCATION = 'nerverdie.db/'


class Datastore:
    class __Datastore:

        def __init__(self, args={}):
            self.args = args
            self.db = plyvel.DB(DB_LOCATION, create_if_missing=True)

        def __str__(self):
            return repr(self) + self.args

        def get(self, name):
            return self.db.get(name);


        def put(self, name, value):
            return self.db.put(name, value);

        def delete(self, name):
            return self.db.delete(name);

        def iterator(self, start, stop = None):
            return self.db.iterator(start=start.encode(), fill_cache=False)

    instance = None

    def __init__(self, args={}):
        if not Datastore.instance:
            Datastore.instance = Datastore.__Datastore(args)
        else:
            Datastore.instance.args = args
    def __getattr__(self, name):
        return getattr(self.instance.args, name)


    def get(self, name):
        return self.instance.get(name)

    def put(self, name, value):
        return self.instance.put(name, value)

    def delete(self, name):
        return self.instance.delete(name)

    def iterator(self, start, stop = None):
        return self.instance.iterator(start, stop)