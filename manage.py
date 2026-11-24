#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User administration.

    python manage.py create-user <username>
    python manage.py set-password <username>
    python manage.py delete-user <username>
    python manage.py list-users
"""

import argparse
import getpass
import sys

from server.models.user import User
from server.storage.main import Datastore

MIN_PASSWORD_LENGTH = 12


def ask_password():
    password = getpass.getpass('Password: ')
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit('Password must be at least %d characters.' % MIN_PASSWORD_LENGTH)
    if getpass.getpass('Confirm password: ') != password:
        sys.exit('Passwords do not match.')
    return password


def main(argv=None):
    parser = argparse.ArgumentParser(description='Neverdie user administration')
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('create-user', 'set-password', 'delete-user'):
        sub.add_parser(name).add_argument('username')
    sub.add_parser('list-users')
    args = parser.parse_args(argv)

    Datastore()

    if args.command == 'list-users':
        for user in User.select().order_by(User.username):
            print(user.username)
        return

    user = User.get_or_none(User.username == args.username)

    if args.command == 'create-user':
        if user is not None:
            sys.exit('User %s already exists.' % args.username)
        user = User(username=args.username)
        user.set_password(ask_password())
        user.save()
        print('User %s created.' % args.username)
    elif user is None:
        sys.exit('Unknown user %s.' % args.username)
    elif args.command == 'set-password':
        user.set_password(ask_password())
        user.save()
        print('Password updated for %s.' % args.username)
    elif args.command == 'delete-user':
        user.delete_instance()
        print('User %s deleted.' % args.username)


if __name__ == '__main__':
    main()
