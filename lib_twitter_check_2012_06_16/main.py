# -*- mode: python; coding: utf-8 -*-
#
# Copyright 2011 Andrej A Antonov <polymorphm@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

assert unicode is not str
assert str is bytes

import argparse, tornado.ioloop
from .twitter_check import check_list_files

def final():
    print('done!')
    tornado.ioloop.IOLoop.instance().stop()

def main():
    parser = argparse.ArgumentParser(
            description='check Twitter accounts')
    parser.add_argument('list', metavar='ACCOUNT-LIST-FILE', nargs='+',
            help='txt-file of Twitter account list in format ``username:password``')
    parser.add_argument('--conc', metavar='CONCURRENCE', type=int,
            help='concurrence')
    parser.add_argument('--delay', metavar='DELAY', type=int,
            help='concurrence')
    parser.add_argument('--out', metavar='OUT-FILE',
            help='output txt-file of Twitter account list with positive result check')
    
    args = parser.parse_args()
    
    check_list_files(args.list, conc=args.conc, delay=args.delay,
            out_list=args.out, callback=final)
    
    tornado.ioloop.IOLoop.instance().start()
