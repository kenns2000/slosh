#!/usr/bin/env python
"""

Copyright (c) 2008  Dustin Sallings <dustin@spy.net>
"""

import sys
from twisted.application import internet, service
from twisted.web import server, resource, static
from twisted.internet import defer

class Topic(resource.Resource):

    def __init__(self):
        self.requests=[]
        self.sessions={}

    def render(self, request):
        if request.method == 'GET':
            session = request.getSession()
            if session.uid not in self.sessions:
                print "New session: ", session.uid
                self.sessions[session.uid] = []
                session.notifyOnExpire(self.__mk_session_exp_cb(session.uid))
            if not self.__deliver(request):
                self.requests.append(request)
            return server.NOT_DONE_YET
        else:
            # Store all the data for all known sessions
            params=str(request.args)
            for sid, a in self.sessions.iteritems():
                print "Queueing to", sid
                a.append(params)
            # Now find all current requests and feed them.
            t=self.requests
            self.requests=[]
            for r in t:
                self.__deliver(r)
            return self.__mk_res(request, 'ok', 'text/plain')

    def __deliver(self, req):
        sid = req.getSession().uid
        data = self.sessions[sid]
        if data:
            print "Delivering to", sid
            self.sessions[sid] = []
            c = '\n'.join(data)
            req.write(self.__mk_res(req, c, 'text/plain'))
            req.finish()
        return data

    def __mk_session_exp_cb(self, sid):
        def f():
            print "Expired session", sid
            del self.sessions[sid]
        return f

    def __mk_res(self, req, s, t):
        req.setHeader("content-type", t)
        req.setHeader("content-length", str(len(s)))
        return s

class TopResource(resource.Resource):

    topics = {}

    def getChild(self, path, request):
        a=path.split('/', 1)
        t=a[0]
        rest = None
        if len(a) > 1: rest=a[1]

        topic = self.topics.get(t, None)
        if not topic:
            topic = Topic()
            self.topics[t] = topic

        return topic

application = service.Application('hpub')
serviceCollection = service.IServiceCollection(application)

# 30s sessions
server.Session.sessionTimeout=10

site = server.Site(TopResource())
site.sessionCheckTime = 5
internet.TCPServer(8000, site).setServiceParent(serviceCollection)