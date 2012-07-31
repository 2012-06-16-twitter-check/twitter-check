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

from __future__ import absolute_import

assert unicode is not str
assert str is bytes

import itertools, functools, datetime
import tornado.ioloop, tornado.stack_context, tornado.gen, \
        tornado.httpclient, tornado.escape
from .async_http_request_helper import async_fetch

DEFAULT_CONCURRENCE = 10
DEFAULT_DELAY = 60.0

def get_username(account_line):
    account = account_line.split(':')
    if len(account) != 2:
        return
    
    return account[0]

@tornado.gen.engine
def check_account(acc_meta, delay=None, proxies=None, callback=None):
    callback = tornado.stack_context.wrap(callback)
    
    if delay is None:
        delay = DEFAULT_DELAY
    delay_deadline = datetime.timedelta(seconds=delay)
    
    io_loop = tornado.ioloop.IOLoop.instance()
    
    def on_error(type, value, traceback):
        if isinstance(value, EnvironmentError):
            io_loop.add_timeout(
                    delay_deadline,
                    functools.partial(callback, False))
            
            return True
    
    with tornado.stack_context.ExceptionStackContext(on_error):
        wait_key = object()
        async_fetch(acc_meta['url'], proxies=proxies,
                callback=(yield tornado.gen.Callback(wait_key)))
        
        response = yield tornado.gen.Wait(wait_key)
    
    if response.code == 200 and acc_meta['username'] in response.body:
        result = True
    else:
        result = False
    
    if callback is not None:
        io_loop.add_timeout(
                delay_deadline,
                functools.partial(callback, result))

@tornado.gen.engine
def check_list(in_list, conc=None, delay=None, proxies=None,
        on_positive=None, on_finish=None):
    on_finish = tornado.stack_context.wrap(on_finish)
    on_positive = tornado.stack_context.wrap(on_positive)
    
    if conc is None:
        conc = DEFAULT_CONCURRENCE
    
    in_list_iter = iter(in_list)
    while True:
        conc_in_list = tuple(itertools.islice(in_list_iter, conc))
        if not conc_in_list:
            break
        
        acc_meta_list = tuple(
                {
                    'account_line': account_line,
                    'username': get_username(account_line),
                    'url': 'http://mobile.twitter.com/{username}'.format(
                            username=tornado.escape.url_escape(get_username(account_line)))
                } for account_line in conc_in_list)
        
        for acc_meta in acc_meta_list:
            print('checking {!r} ({!r})...'.format(
                    acc_meta['username'], acc_meta['url']))
            
            acc_meta['wait_key'] = object()
            check_account(acc_meta, delay=delay, proxies=proxies,
                    callback=(yield tornado.gen.Callback(acc_meta['wait_key'])))
        
        for acc_meta in acc_meta_list:
            acc_meta['result'] = yield tornado.gen.Wait(acc_meta['wait_key'])
            
            if acc_meta['result']:
                print('{!r} ({!r}) is **positive**!'.format(
                        acc_meta['username'], acc_meta['url']))
                
                if on_positive is not None:
                    on_positive(
                            acc_meta['account_line'], acc_meta['username'])
            else:
                print('{!r} ({!r}) is negative!'.format(
                        acc_meta['username'], acc_meta['url']))
    
    if on_finish is not None:
        on_finish()

@tornado.gen.engine
def check_list_files(in_list_files, conc=None, delay=None, proxies=None,
        out_list=None, callback=None, on_positive=None):
    callback = tornado.stack_context.wrap(callback)
    on_positive = tornado.stack_context.wrap(on_positive)
    
    in_list = []
    
    for in_list_file in in_list_files:
        with open(in_list_file) as in_fd:
            for raw_line in in_fd:
                line = raw_line.strip()
                if not line:
                    continue
                
                in_list.append(line)
    
    if out_list is not None:
        out_fd = open(out_list, 'w')
        def on_check_list_files_positive(account_line, username):
            out_fd.write('{}\n'.format(account_line))
            out_fd.flush()
            
            if on_positive is not None:
                on_positive(account_line, username)
    else:
        out_fd = None
        def on_check_list_files_positive(account_line, username):
            if on_positive is not None:
                on_positive(account_line, username)
    
    wait_key = object()
    check_list(in_list, conc=conc, delay=delay, proxies=proxies,
            on_finish=(yield tornado.gen.Callback(wait_key)),
            on_positive=on_check_list_files_positive)
    yield tornado.gen.Wait(wait_key)
    
    if out_fd is not None:
        out_fd.close()
    
    if callback is not None:
        callback()
