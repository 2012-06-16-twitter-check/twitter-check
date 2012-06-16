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

import itertools
import tornado.stack_context, tornado.gen, tornado.httpclient, \
        tornado.escape

CONCURRENCE = 10

def get_username(account_line):
    account = account_line.split(':')
    if len(account) != 2:
        return
    
    return account[0]

@tornado.gen.engine
def check_account(account_line, username, callback=None):
    callback = tornado.stack_context.wrap(callback)
    
    url = 'https://mobile.twitter.com/{username}'.format(
            username=tornado.escape.url_escape(username))
    
    wait_key = object()
    http_client = tornado.httpclient.AsyncHTTPClient()
    http_client.fetch(
            url,
            follow_redirects=False,
            callback=(yield tornado.gen.Callback(wait_key)))
    
    response = yield tornado.gen.Wait(wait_key)
    
    if not response.error and response.code == 200 and \
            'class="profile-details"' in response.body:
        result = True
    else:
        result = False
    
    if callback is not None:
        callback(result)

@tornado.gen.engine
def check_list(in_list, conc=None, on_positive=None, on_finish=None):
    on_finish = tornado.stack_context.wrap(on_finish)
    on_positive = tornado.stack_context.wrap(on_positive)
    
    if conc is None:
        conc = CONCURRENCE
    
    in_list_iter = iter(in_list)
    while True:
        conc_in_list = list(itertools.islice(in_list_iter, conc))
        if not conc_in_list:
            break
        
        conc_meta_list = tuple(
                {
                    'account_line': account_line,
                    'username': get_username(account_line),
                } for account_line in conc_in_list)
        
        for conc_meta in conc_meta_list:
            print('checking {!r}...'.format(conc_meta['username']))
            
            conc_meta['wait_key'] = object()
            check_account(conc_meta['account_line'], conc_meta['username'],
                    callback=(yield tornado.gen.Callback(conc_meta['wait_key'])))
        
        for conc_meta in conc_meta_list:
            conc_meta['result'] = yield tornado.gen.Wait(conc_meta['wait_key'])
            
            if conc_meta['result']:
                print('{!r} is **positive**!'.format(conc_meta['username']))
                
                if on_positive is not None:
                    on_positive(
                            conc_meta['account_line'], conc_meta['username'])
            else:
                print('{!r} is negative!'.format(conc_meta['username']))
    
    if on_finish is not None:
        on_finish()

@tornado.gen.engine
def check_list_files(in_list_files, conc=None,
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
    check_list(in_list,
            conc=conc,
            on_finish=(yield tornado.gen.Callback(wait_key)),
            on_positive=on_check_list_files_positive)
    yield tornado.gen.Wait(wait_key)
    
    if out_fd is not None:
        out_fd.close()
    
    if callback is not None:
        callback()
