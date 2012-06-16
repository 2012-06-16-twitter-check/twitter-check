# -*- mode: python; coding: utf-8 -*-
#
# Copyright 2011, 2012 Andrej A Antonov <polymorphm@gmail.com>.
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

import urllib2
from .daemon_async import daemon_async

REQUEST_TIMEOUT = 20.0
RESPONSE_BODY_LENGTH_LIMIT = 100000000

class Response:
    pass

@daemon_async
def async_fetch(url, data=None, proxies=None):
    build_opener_args = []
    if proxies is not None:
        build_opener_args.append(
                urllib2.ProxyHandler(proxies=proxies))
    
    opener = urllib2.build_opener(*build_opener_args)
    f = opener.open(url, data=data, timeout=REQUEST_TIMEOUT)
    
    response = Response()
    response.code = f.getcode()
    response.body = f.read(RESPONSE_BODY_LENGTH_LIMIT)
    
    return response
