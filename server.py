import os, sys
import traceback, logging
import werkzeug
from werkzeug.serving import WSGIRequestHandler
            
from StringIO import StringIO

class StreamRequest(object):
    '''
    wrapper class for two StringIO objects provided by StringWSGIServer.
    this class can be used by WSGIRequestHandler to access streams through
    its base classes. note the inheritance tree for the handler: 
        
        SocketServer.StreamRequestHandler
                ^
                |
        BaseHTTPRequestHandler
                ^
                |
        WSGIRequestHandler
    
    the base classes expect to be interacting with a StreamServer of some
    kind, which produces a request object and gives it off to the handler.
    The handler then calls request.creates handler.rfile and handler.wfile, 
    which are file-handle-like objects for reading the request and writing the
    response. In the case of a StreamServer, the file-likes are sockets.
    For responding to in memory strs used by StringWSGIServer, the file-likes
    are StringIO objects.
    '''
    def __init__(self, read_file, write_file):
        self.read_file = read_file
        self.write_file = write_file
        
    def settimeout(self):
        raise Exception('NotImplemented')
        
    def setsockopt(self, *args):
        raise Exception('NotImplemented')
        
    def makefile(self, mode, bufsize):
        '''
        mode: 'rb', 'wb'
        bufsize: 0 or -1. StringIOs are buffered either way.
        '''
        if mode == 'rb':
            return self.read_file
        elif mode == 'wb':
            return self.write_file
        raise Exception('NotImplemented')
        
class StringIOWrap(StringIO):
    ''' wrap StringIO so we can prevent a call to close() '''
    def close(self):
        pass
        
import time
G_LOGGER = logging.getLogger('wsgi_server')
G_HANDLER = logging.FileHandler('wsgi_server.log')
G_HANDLER.setLevel(logging.DEBUG)
G_LOGGER.addHandler(G_HANDLER)
G_LOGGER.setLevel(logging.DEBUG)
def log(message):
    now = time.time()
    weekdayname = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
    s = "%02d/%3s/%04d %02d:%02d:%02d" % (
            day, monthname[month], year, hh, mm, ss)

    txt = '-- [{}] {}\n\n'.format(s, message)
    #print txt
    G_LOGGER.debug(txt)
    

class StringWSGIServer(object):
    ''' 
    a single process, single thread wsgi server that doesnt open a socket
    but instead expects to be called with a string blob that contains
    the HTTP request contents
    '''
    multithread = False
    multiprocess = False
    
    def __init__(self, application, use_debugger=False, use_evalex=True):
        '''
        :param use_debugger: should the werkzeug debugging system be used?
        :param use_evalex: should the exception evaluation feature be enabled?
        selfhost is intended to indicate in process HTTP serving
        '''
        if use_debugger:
            from werkzeug.debug import DebuggedApplication
            application = DebuggedApplication(application, use_evalex)        
        self.app = application
        self.ssl_context = None
        self.server_address = ('selfhost', 0)
        self.shutdown_signal = None 
        self.passthrough_errors = True        
        
    def respond(self, request_text):
        ''' 
        parse the HTTP request text and return an HTTP response text. 
        WSGIRequestHandler's __init__ comes all the way from great
        great grandparent BaseRequestHandler
        this class should fullfil all of the requirements of server
        '''
        read_file = StringIOWrap(request_text)
        write_file = StringIOWrap()
        handler = WSGIRequestHandler(StreamRequest(read_file, write_file), 
                                    self.server_address, self)        
        response_text = write_file.getvalue()
        log(request_text[:200])
        log(response_text[:200])
        return response_text
        
G_SERVER = []
G_FIRST = True
        
def wsgi_response(application, request_text):
    '''  process HTTP request and return an HTTP response '''
    global G_SERVER
    global G_FIRST
    if G_FIRST:
        log('initializing server')
        G_FIRST = False
        G_SERVER = StringWSGIServer(application)
        
    try:
        return G_SERVER.respond(request_text)
    except:
        log(traceback.format_exc())
    return 'HTTP/1.0 500 ERROR'
    
    
from flask import Flask, request
app = Flask(__name__)

@app.route('/login', methods=['GET', 'POST'])
def login():
    print request
    return 'LOGIN SUCCESS for user {}'.format(request.form['userid'])
    
def test():
    ''' post text courtesy sun.com '''
    request = \
"""POST /login HTTP/1.1
Host: www.mysite.com
User-Agent: Mozilla/4.0
Content-Length: 27
Content-Type: application/x-www-form-urlencoded

userid=joe&password=guessme"""

    expect = \
"""HTTP/1.0 200 OK
Content-Type: text/html; charset=utf-8
Content-Length: 26
Server: Werkzeug/0.8.3 Python/2.7.2
Date: Fri, 02 Mar 2012 20:41:15 GMT

LOGIN SUCCESS for user joe"""
        
    print wsgi_response(app, request)
    print wsgi_response(app, request)
    print wsgi_response(app, request)
    
    
if __name__=='__main__':
    test()