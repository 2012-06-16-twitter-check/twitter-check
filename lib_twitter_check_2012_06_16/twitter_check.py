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

import functools, datetime
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
def check_list_thread(in_list_iter, delay=None, proxies=None,
        on_positive=None, on_negative=None,
        on_check_open=None, on_check_finish=None, on_finish=None):
    on_check_open = tornado.stack_context.wrap(on_check_open)
    on_check_finish = tornado.stack_context.wrap(on_check_finish)
    on_positive = tornado.stack_context.wrap(on_positive)
    on_negative = tornado.stack_context.wrap(on_negative)
    on_finish = tornado.stack_context.wrap(on_finish)
    
    for account_line in in_list_iter:
        username = get_username(account_line)
        url = 'http://mobile.twitter.com/{username}'.format(
                    username=tornado.escape.url_escape(username))
        acc_meta = {
            'account_line': account_line,
            'username': username,
            'url': url,
        }
        
        print('checking {!r} ({!r})...'.format(username, url))
        
        if on_check_open is not None:
            on_check_open(acc_meta)
        
        wait_key = object()
        check_account(acc_meta, delay=delay, proxies=proxies,
                callback=(yield tornado.gen.Callback(wait_key)))
        
        result = yield tornado.gen.Wait(wait_key)
        
        if result:
            print('{!r} ({!r}) is **positive**!'.format(username, url))
            
            if on_positive is not None:
                on_positive(acc_meta)
        else:
            print('{!r} ({!r}) is negative!'.format(username, url))
            
            if on_negative is not None:
                on_negative(acc_meta)
        
        if on_check_finish is not None:
            on_check_finish(acc_meta)
    
    if on_finish is not None:
        on_finish()

@tornado.gen.engine
def bulk_check_list(in_list, conc=None, delay=None, proxies=None,
        on_positive=None, on_negative=None,
        on_check_open=None, on_check_finish=None, on_finish=None):
    on_check_open = tornado.stack_context.wrap(on_check_open)
    on_check_finish = tornado.stack_context.wrap(on_check_finish)
    on_positive = tornado.stack_context.wrap(on_positive)
    on_negative = tornado.stack_context.wrap(on_negative)
    on_finish = tornado.stack_context.wrap(on_finish)
    
    if conc is None:
        conc = DEFAULT_CONCURRENCE
    
    in_list_iter = iter(in_list)
    wait_key_list = tuple(object() for x in xrange(conc))
    
    for wait_key in wait_key_list:
        check_list_thread(in_list_iter, delay=delay, proxies=proxies,
                on_positive=on_positive, on_negative=on_negative,
                on_check_open=on_check_open, on_check_finish=on_check_finish,
                on_finish=(yield tornado.gen.Callback(wait_key)))
    
    for wait_key in wait_key_list:
        yield tornado.gen.Wait(wait_key)
    
    if on_finish is not None:
        on_finish()

@tornado.gen.engine
def check_list_files(in_list_files, conc=None, delay=None, proxies=None,
        out_list=None, callback=None):
    callback = tornado.stack_context.wrap(callback)
    
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
        def on_check_list_files_positive(acc_meta):
            account_line = acc_meta['account_line']
            username =  acc_meta['username']
            
            out_fd.write('{}\n'.format(account_line))
            out_fd.flush()
    else:
        out_fd = None
        on_check_list_files_positive = None
    
    wait_key = object()
    bulk_check_list(in_list, conc=conc, delay=delay, proxies=proxies,
            on_finish=(yield tornado.gen.Callback(wait_key)),
            on_positive=on_check_list_files_positive)
    yield tornado.gen.Wait(wait_key)
    
    if out_fd is not None:
        out_fd.close()
    
    if callback is not None:
        callback()
