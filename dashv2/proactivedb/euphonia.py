#!/usr/bin/env python

import argumentparserpp
import bottle
import bson
import bson.json_util
import bson.son
import daemon
import karakuriclient
import logging
import os
import pidlockfile
import pymongo
import pytz
import re
import signal
import string
import sys
import urlparse
import math
import json

from datetime import datetime, timedelta
from models import groups, tests, mdiag
from sfdcpp import sfdcpp
from wsgiproxy.app import WSGIProxyApp

utc = pytz.UTC


class Euphonia():
    def __init__(self, args):
        # Expect args from karakuriparser
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.logger = logging.getLogger('logger')

        self.kk = karakuriclient.karakuriclient(args)
        self.sfdc = None

        # Output args for debugging
        self.logger.debug("parsed args:")
        for arg in self.args:
            if "password" in arg or "passwd" in arg or "token" in arg:
                tmp = "[REDACTED]"
            else:
                tmp = self.args[arg]
            self.logger.debug("%s %s" % (arg, tmp))

        self.token = self.args['token']

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.db_euphonia = self.mongo.euphonia
        self.db_support = self.mongo.support
        self.coll_failedtests = self.db_euphonia.failedtests
        self.coll_groups = self.db_euphonia.groups
        self.coll_tests = self.db_euphonia.tests
        self.coll_companies = self.db_support.companies
        self.coll_issues = self.db_support.issues

        self.lastCacheUpdate = None

    def mmsGroupIdToCompanyId(self, gid):
        # gid -> gName (groupName)
        try:
            res = self.coll_groups.find_one({'_id':gid}, {'name':1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if res is None:
            return {'ok': False, 'payload': 'Group not found for %s' % gid}
        gName = res['name']

        # gName -> companyId
        try:
            res = self.coll_companies.find_one({"$or": [{"mms_groups": gName}, {"jira_groups": gName}]}, {'_id': 1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if res is None:
            return {'ok': False, 'payload': 'Company not found for %s' % gName}
        return {'ok': True, 'payload': res['_id']}

    def mmsGroupIdToSFProjectId(self, gid):
        # gid -> gName (groupName)
        try:
            res = self.coll_groups.find_one({'_id':gid}, {'name':1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if res is None:
            return {'ok': False, 'payload': 'Group not found for %s' % gid}
        gName = res['name']

        # gName -> companyId
        try:
            res = self.coll_companies.find_one({"$or":[{"mms_groups": gName}, {"jira_groups": gName}]}, {'sf_project_id': 1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if res is None:
            return {'ok': False, 'payload': 'Company not found for %s' % gName}
        return {'ok': True, 'payload': res['sf_project_id']}

    def addGroupNote(self, gid, text, **kwargs):
        """ Add a note to the associated salesforce project """
        res = self.mmsGroupIdToCompanyId(gid)
        if not res['ok']:
            return res
        companyId = res['payload']
        title = "ProactiveDB: Added by %s" % kwargs['token']
        # TODO these sfdc methods should take sfIds, not companyId
        # the mmsGroupIdToSF* methods above should go to python-lib
        # and used everywhere
        res = self.sfdc.addSFPublicProjectNote(companyId, title, text)
        if not res['ok']:
            return res
        epoch = datetime.fromtimestamp(0)
        createdDateTS = int((datetime.now()-epoch).total_seconds())
        lastModifiedDateTS = int((datetime.now()-epoch).total_seconds())
        note = {'sfid': res['payload']['id'], 'author': kwargs['token'], 'text': text, 'createdDateTS': createdDateTS, 'lastModifiedDateTS': lastModifiedDateTS}
        return {'ok': True, 'payload': note}

    def editGroupNote(self, sfid, text, **kwargs):
        """ Update the note with the given salesforce id """
        res = self.sfdc.editSFNote(sfid, text)
        if not res['ok']:
            return res
        note = {'sfid': sfid, 'text': text}
        return {'ok': True, 'payload': note}

    def deleteGroupNote(self, sfid, **kwargs):
        """ Delete the note with the given salesforce id """
        res = self.sfdc.deleteSFNote(sfid)
        if not res['ok']:
            return res
        return {'ok': True, 'payload': None}

    def getGroupNotes(self, gid, **kwargs):
        """ Get ProactiveDB notes from the associated salesforce project """
        # res = self.mmsGroupIdToCompanyId(gid)
        # if not res['ok']:
        #     return res
        # companyId = res['payload']
        #
        # res = self.sfdc._getProjectId(companyId)
        # if not res['ok']:
        #     return res
        # sfProjectId = res['payload']
        #
        # query = "SELECT Id,Title,Body,CreatedDate,LastModifiedDate FROM Note WHERE ParentId='%s' AND Title LIKE 'ProactiveDB:%%' ORDER BY CreatedDate DESC" % sfProjectId
        # # TODO rename querySFDC to just query geesh
        # res = self.sfdc.querySFDC(query)
        # if not res['ok']:
        #     return res
        # notes = res['payload']
        # self.logger.debug(notes)
        
        notes = []
        res = []
        for note in notes:
            # TODO regex author from title
            m = re.search('ProactiveDB: Added by ((\w|\W)+)', note['Title'])
            if m is not None:
                author = m.group(1)
            else:
                author = "SomeDude"
            createdDate = note['CreatedDate']
            lastModifiedDate = note['LastModifiedDate']
            epoch = datetime.fromtimestamp(0)
            res.append({'sfid': note['Id'], 'author': author,
                        'text': note['Body'],
                        'createdDateTS': (createdDate-epoch).total_seconds(),
                        'lastModifiedDateTS': (lastModifiedDate-epoch).total_seconds()})
        return {'ok': True, 'payload': res}

    def removeNote(self, gid, noteId):
        pass

    def _getTemplateValue(self, var, groupSummary, testDoc=None):
        """ Return a value for the given template variable. A finite number of
        such template variables are supported and defined below """
        self.logger.debug("_getTemplateValue(%s,%s)", var, None)
        if var == "MMS_GROUP_NAME":
            if 'name' in groupSummary:
                return {'ok': True, 'payload': groupSummary['name']}
        elif var == "MMS_GROUP_ID":
            if '_id' in groupSummary:
                return {'ok': True, 'payload': groupSummary['_id']}
        elif var == "MMS_GROUP_ANCHOR":
            if 'name' in groupSummary:
                gid = groupSummary['_id']
                url = 'https://mms.mongodb.com/host/list/%s' % gid
                return {'ok': True, 'payload': '<a href="%s">%s</a>' %
                        (url, groupSummary['name'])}
        elif var == "LIST_AFFECTED_HOSTS":
            if testDoc is not None and 'ids' in testDoc:
                res = ""
                for _id in testDoc['ids']:
                    ping = groupSummary['ids'][_id.__str__()]
                    doc = ping['doc']
                    res += '# [%s:%s|https://mms.mongodb.com/host/detail/%s/%s]\n' %\
                           (doc['host'], doc['port'], ping['gid'], ping['hid'])
                return {'ok': True, 'payload': res}
        elif var == "LINK_AFFECTED_HOSTS_UL":
            if testDoc is not None and 'ids' in testDoc:
                res = ""
                for _id in testDoc['ids']:
                    ping = groupSummary['ids'][_id.__str__()]
                    doc = ping['doc']
                    res += '* [https://mms.mongodb.com/host/detail/%s/%s|%s:%s]>\n' %\
                           (ping['gid'], ping['hid'], doc['host'], doc['port'])
                return {'ok': True, 'payload': res}
        elif var == "LIST_AFFECTED_HOSTS_UL":
            if testDoc is not None and 'ids' in testDoc:
                res = ""
                for _id in testDoc['ids']:
                    # Make sure we still have this ping, could be deleted
                    if _id.__str__() not in groupSummary['ids']:
                        continue
                    ping = groupSummary['ids'][_id.__str__()]
                    doc = ping['doc']
                    res += '* %s:%s\n' % (doc['host'], doc['port'])
                return {'ok': True, 'payload': res}
        elif var == "N_AFFECTED_HOSTS":
            if testDoc is not None and 'nids' in testDoc:
                return {'ok': True, 'payload': testDoc['nids']}
        elif var == "REPORTER_NAME":
                return {'ok': True,
                        'payload': bottle.request.get_cookie("name")}
        elif var == "SALES_REP":
            company = ['company']
            if company is not None and 'sales' in company and\
                    company['sales'] is not None:
                sales = ['[~' + name['jira'] + ']' for name in company[
                    'sales']]
                return {'ok': True, 'payload': string.join(sales, ', ')}
        return {'ok': False, 'payload': None}

    def healthcheck(self, **kwargs):
        """ Perform various sanity checks on the system """
        isOk = True
        messages = []
        # Are we locked out of MongoDB?
        if self.mongo.is_locked is True:
            isOk = False
            messages.append("euphonia: mongo is locked, no write access")
        # Can we read from the collections we care about?
        try:
            self.coll_failedtests.find_one({}, {'_id': 1})
            self.coll_groups.find_one({}, {'_id': 1})
            self.coll_tests.find_one({}, {'_id': 1})
            self.coll_companies.find_one({}, {'_id': 1})
            self.coll_issues.find_one({}, {'_id': 1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            isOk = False
            messages.append("euphonia: unable to read from mongo: %s" % e)
        return {'ok': bool(isOk), 'payload': messages}

    def renderTemplatedComment(self, comment, group_summary, testDoc):
        # Replace template variables with real values. A template variable is
        # identified as capital letters between double square brackets
        pattern = re.compile('\[\[([A-Z_]+)\]\]')
        matches = set(pattern.findall(comment))
        for match in matches:
            res = self._getTemplateValue(match, group_summary, testDoc)
            if not res['ok']:
                continue
            val = res['payload']
            comment = comment.replace('[[%s]]' % match, str(val))
        return comment

    def setSfdc(self, sfdc):
        """ Set SFDC """
        self.sfdc = sfdc

    def updateTestDescriptionCache(self):
        """ Fetch and cache latest test descriptions """
        self.logger.debug("updateTestDescriptionCache()")
        self.testDescriptionCache = {
            "greeting": "Hi",
            "opening": "My name is [[REPORTER_NAME]] and I am a member of "
                       "the Proactive Technical Support team here at "
                       "MongoDB, Inc. There are issues in your MMS group "
                       "[[[MMS_GROUP_NAME]]|https://mms.mongodb.com/host/"
                       "list/[[MMS_GROUP_ID]]] that we would like to "
                       "address in this ticket. It's possible that we "
                       "will discover more issues during the diagnostic "
                       "process, and we will address those in turn.",
            "closing": "We look forward to working with you to resolve "
                       "the issues described above. Please review them "
                       "at your earliest convenience and let us know if we "
                       "can be of help in addressing them.",
            "signoff": "Thanks, The MongoDB Proactive Services Team"
        }

        try:
            curr_tests = self.coll_tests.find({}, {'_id': 0})
        except pymongo.errors.PyMongoError as e:
            raise e
        if curr_tests is not None:
            for test in curr_tests:
                if test['src'] in self.testDescriptionCache:
                    self.testDescriptionCache[test['src']][test['name']] = test
                else:
                    self.testDescriptionCache[test['src']] =\
                        {test['name']: test}

        self.lastCacheUpdate = datetime.now()

    def start(self):
        g = groups.Groups(self.mongo)
        t = tests.Tests(self.db_euphonia)
        # sf = salesforce_client.Salesforce(self.args)
        md = mdiag.Mdiag(self.mongo)

        # populate testDescriptionCache
        self.updateTestDescriptionCache()

        b = bottle.Bottle(autojson=False)

        proxy_app = WSGIProxyApp("http://sdash-1.10gen.cc:9200/")

        FILTER_HEADERS = [
            'Connection',
            'Keep-Alive',
            'Proxy-Authenticate',
            'Proxy-Authorization',
            'TE',
            'Trailers',
            'Transfer-Encoding',
            'Upgrade',
            ]

        def wrap_start_response(start_response):
            def wrapped_start_response(status, headers_out):
                # Remove "hop-by-hop" headers
                headers_out = [(k,v) for (k,v) in headers_out
                               if k not in FILTER_HEADERS]
                return start_response(status, headers_out)
            return wrapped_start_response


        def wrapped_proxy_app(environ, start_response):
            start_response = wrap_start_response(start_response)
            return proxy_app(environ, start_response)

        b.mount("/elasticsearch", wrapped_proxy_app)

        bottle.TEMPLATE_PATH.insert(0, '%s/views' % self.args['root_webdir'])

        @b.hook('before_request')
        def updateCaches():
            """ If it's been more than a minute since the last time we updated
            our various caches, update them """
            if self.lastCacheUpdate+timedelta(minutes=1) <\
                    datetime.now():
                self.updateTestDescriptionCache()

        def response(result, cookies=None, template=None, template_data=None):
            if result['status'] == "success":
                if cookies is not None:
                    for cookie in cookies:
                        if not isinstance(cookie[1], unicode):
                            try:
                                val = bson.json_util.dumps(cookie[1])
                            except Exception as e:
                                val = e
                        else:
                            val = cookie[1]
                        bottle.response.set_cookie(str(cookie[0]), val)
                bottle.response.status = 200
                if template is not None:
                    data = {'data': result['data']}
                    if template_data is not None:
                        for datum in template_data:
                            data[datum] = template_data[datum]
                    return bottle.template(template, data=data)
            elif result['status'] == "fail":
                bottle.response.status = 500
            elif result['status'] == "error":
                bottle.response.status = 400
            return bson.json_util.dumps(result)

        def tokenize(func):
            """ A decorator for bottle-route callback functions to pass
            auth_user cookies """
            def wrapped(*args, **kwargs):
                # NOTE this is a corp cookie!
                kwargs['token'] = bottle.request.get_cookie("auth_user", '')
                # unescape escaped html characters!!
                # just @ for now as there are plenty of user@10gen.com's
                if kwargs['token'] is not None:
                    kwargs['token'] = kwargs['token'].replace('%40', '@')
                return func(*args, **kwargs)
            return wrapped

        def error(message=None):
            ret = {'status': 'error', 'message': str(message)}
            bottle.response.status = 403
            return bson.json_util.dumps(ret)

        @b.route('/shouldirespond')
        def shouldIRespond():
            return bottle.template('base_page', renderpage="shouldirespond")

        @b.post('/login')
        def login():
            token = bottle.request.get_cookie("auth_user")
            if token is None:
                return error("Login to corp")
            # unescape escaped html characters!!
            # just @ for now as there are plenty of user@10gen.com's
            token = token.replace('%40', '@')
            res = self.kk.postRequest("/login", data={'kk_token': token})
            if res['status'] == 'success':
                user = res['data']
                cookies = [(prop, user[prop]) for prop in user]
            else:
                cookies = None
            return response(res, cookies=cookies)

        # ROOT/SUMMARY PAGE
        @b.route('/')
        def index():
            return bottle.redirect('/tasks')

        @b.route('/monitor')
        def monitor(**kwargs):
            """ Check essential services and ack their status """
            self.logger.debug("health()")
            ret = {'status': 'unsure', 'messages': []}
            res = self.healthcheck(**kwargs)
            if res['ok'] is True:
                ret['messages'].append('Healthy as a fox, thanks for checking!')
                ret['status'] = 'OK'
            else:
                ret['status'] = 'bad'
            if res['payload'] is not None:
                ret['messages'].extend(res['payload'])
            return bson.json_util.dumps(ret)

        # GROUP-RELATED ROUTES
        @b.route('/groups/<page>/<query>')
        @b.route('/groups/<page>')
        @b.route('/groups')
        @b.route('/groups/')
        def get_groups(page=1, query=None):
            match = {'failedTests': {"$exists": 1}}
            if query is not None:
                qstring = "%s" % query
                regex = re.compile(qstring, re.IGNORECASE)
                match['name'] = regex

            limit = 25
            if page == '':
                page = 1
            page = int(page)
            skip = (page - 1) * limit

            groupsTotal = 0

            try:
                res = self.coll_groups.find(match).\
                    sort('score', pymongo.DESCENDING).limit(limit).skip(skip)
                groupsTotal = self.coll_groups.find(match).count()
            except pymongo.errors.PyMongoError as e:
                self.logger.exception(e)

            groups = [group for group in res]

            pagesTotal = int(math.ceil(groupsTotal/limit))
            return bottle.template('base_page', renderpage="summary",
                                   groups=groups, page=page,issue=None, query=query,
                                   count=groupsTotal, pagesTotal=pagesTotal)

        @b.post('/addnote')
        @tokenize
        def add_note(**kwargs):
            params = json.load(bottle.request.body)
            res = self.addGroupNote(params['gid'], params['text'], **kwargs);
            if res['ok'] is True:
                return bson.json_util.dumps({"status": "success", "data": res['payload']})
            else:
                return error(res['payload'])

        @b.post('/editnote')
        @tokenize
        def add_note(**kwargs):
            params = json.load(bottle.request.body)
            res = self.editGroupNote(params['sfid'], params['text'], **kwargs);
            if res['ok'] is True:
                return bson.json_util.dumps({"status": "success", "data": res['payload']})
            else:
                return error(res['payload'])

        @b.post('/deletenote')
        @tokenize
        def add_note(**kwargs):
            params = json.load(bottle.request.body)
            res = self.deleteGroupNote(params['sfid'], **kwargs);
            if res['ok'] is True:
                return bson.json_util.dumps({"status": "success", "data": res['payload']})
            else:
                return error(res['payload'])

        @b.route('/analysis/page/<page>')
        @b.route('/analysis')
        def get_companies(page=1, test=None, query=None):
            match = {}
            limit = 25
            if page == '':
                page = 1
            page = int(page)
            skip = (page - 1) * limit

            companiestotal = 0

            try:
                res = self.coll_companies.find(match).\
                    sort('_id', pymongo.ASCENDING).skip(skip).limit(limit)
                companiestotal = self.coll_companies.find(match).count()
            except pymongo.errors.PyMongoError as e:
                self.logger.exception(e)

            companies = []
            for company in res:
                companyticketcount = self.coll_issues.find({'jira.fields.customfield_10030.name': company['_id']}).count()
                company['ticketcount'] = companyticketcount

                tres = self.coll_issues.\
                        find({'jira.fields.customfield_10030.name': company['_id']},
                             {'jira.fields.created': 1}).\
                                     sort('jira.fields.created', pymongo.DESCENDING).limit(1)
                companylastticket = next(tres, None)
                company['lastticket'] = None

                if companylastticket is not None:
                    company['lastticket'] = companylastticket['jira']['fields']['created']
                companies.append(company)
            pagesTotal = int(math.ceil(companiestotal/limit))
            return bottle.template('base_page', renderpage="analysis",
                                   companies=companies, page=page,
                                   count=companiestotal, pagesTotal=pagesTotal)

        @b.route('/group/<gid>')
        def get_group_summary(gid):
            group_summary = g.getGroupSummary(gid)
            res = self.getGroupNotes(gid)
            if not res['ok']:
                self.logger.warning("Failed to get notes for group %s", gid)
                group_summary['notes'] = []
            else:
                group_summary['notes'] = res['payload']

            testDescriptionCache = {}
            testDescriptionCache['greeting'] = self.renderTemplatedComment(
                self.testDescriptionCache['greeting'], group_summary, None)
            testDescriptionCache['opening'] = self.renderTemplatedComment(
                self.testDescriptionCache['opening'], group_summary, None)
            testDescriptionCache['closing'] = self.renderTemplatedComment(
                self.testDescriptionCache['closing'], group_summary, None)
            testDescriptionCache['signoff'] = self.renderTemplatedComment(
                self.testDescriptionCache['signoff'], group_summary, None)
            for ft in group_summary['failedTests']:
                if ft['src'] not in testDescriptionCache:
                    testDescriptionCache[ft['src']] = {}
                if ft['test'] not in testDescriptionCache[ft['src']]:
                    testDescriptionCache[ft['src']][ft['test']] = {}
                # render templated comment for this test
                try:
                    comment = self.testDescriptionCache[ft['src']][ft['test']][
                        'comment']
                    testDescriptionCache[ft['src']][ft['test']]['comment'] = self.\
                        renderTemplatedComment(comment, group_summary, ft)
                    testDescriptionCache[ft['src']][ft['test']]['header'] = self.\
                            testDescriptionCache[ft['src']][ft['test']]['header']
                except Exception as exc:
                    self.logger.exception(exc)

            if group_summary is not None:
                return bottle.template(
                    'base_page', renderpage="group",
                    group=group_summary,
                    testDescriptionCache=testDescriptionCache)
            else:
                return bottle.redirect('/groups')

        @b.route('/group/<gid>/ignore/<test>')
        def ignore_test(gid, test):
            g.ignore_test(gid, test)
            return bottle.redirect('/group/%s' % gid)

        @b.route('/group/<gid>/include/<test>')
        def include_test(gid, test):
            g.include_test(gid, test)
            return bottle.redirect('/group/%s' % gid)

        # TEST-RELATED ROUTES
        @b.route('/tests')
        def get_failed_tests_summary():
            return bottle.template('base_page', renderpage="tests")

        @b.route('/test')
        def get_tests():
            tobj = t.get_tests()
            output = {"status": "success", "data": {"tests": tobj}}
            return bson.json_util.dumps(output)

        @b.route('/defined_tests')
        def get_tests2():
            tobj = t.get_defined_tests()
            output = {"status": "success", "data": {"defined_tests": tobj}}
            return bson.json_util.dumps(output)

        @b.route('/test/<test>')
        def get_matching_groups(test):
            if test is not None:
                query = {"failedTests.test": test}
                tobj = g.get_failed_tests_summary(sort=[
                    ("priority", pymongo.DESCENDING),
                    ("GroupName", pymongo.ASCENDING)],
                    skip=0, limit=10, query=query)
                output = {"status": "success", "data": tobj}
                return bson.json_util.dumps(output)
            else:
                output = {"status": "success", "data": {}}
                return bson.json_util.dumps(output)

        @b.post('/test')
        def create_test():
            formcontent = bottle.request.body.read()
            test = bson.json_util.loads(formcontent)['test']
            return bson.json_util.dumps(t.create_test(test))

        @b.post('/test/<test_name>')
        def update_test(test_name):
            formcontent = bottle.request.body.read()
            test = bson.json_util.loads(formcontent)['test']
            test_id = bson.json_util.ObjectId(test['_id'])
            test['_id'] = test_id
            return bson.json_util.dumps(t.update_test(test_name, test))

        @b.delete('/test/<test_name>')
        def delete_test(test_name):
            return bson.json_util.dumps(t.delete_test(test_name))

        def render_issue_description(params):
            gid = params['gid']
            ggroupsummary = g.getGroupSummary(gid)
            gfailedtests = ggroupsummary['failedTests']

            renderedIntro = self.renderTemplatedComment(params['intro'], ggroupsummary, None)
            renderedOutro = self.renderTemplatedComment(params['outro'], ggroupsummary, None)

            testlist = []
            if 'tests' in params:
                testlist = params['tests']

            renderedComments = []
            for test in testlist:
                for tid, tcomment in test.iteritems():
                    failedtest = None
                    for ftest in gfailedtests:
                        if str(ftest['_id']) == str(tid):
                            failedtest = ftest
                    rendered = self.renderTemplatedComment(tcomment, ggroupsummary, failedtest)
                    renderedComments.append(rendered)

            renderedComments = '\n'.join(renderedComments)
            renderedTicket = '\n'.join([renderedIntro, renderedComments, renderedOutro])
            return renderedTicket

        # ISSUE ROUTES
        @b.post('/issue')
        @tokenize
        def create_issue(**kwargs):
            params = json.load(bottle.request.body)
            params['issuetype'] = 'Proactive'
            if 'project' not in params:
                params['project'] = 'DAN'
            if 'priority' not in params:
                params['priority'] = 4
            params['reporter'] = 'proactive-support'
            # TODO this is a placeholder for a future in which
            # a debug mode will default to creating DAN tickets
            if params['project'] == 'DAN':
                params['company groups'] = "Jake's Test Group"
            # NOTE the company is not yet set as they will see
            # the ticket upon creation and i am paranoid!!!!!!!
            params['description'] = render_issue_description(params)
            tests = params['tests']
            testIds = [bson.ObjectId(test.keys()[0]) for test in tests]
            # Post ticket creation "callback" actions for karakuri
            params['karakuri'] = []
            adc = {'addDeveloperComment':
                   'https://proactive.corp.mongodb.com/group/%s' %\
                           params['gid']}
            params['karakuri'].append(adc)
            del params['intro']
            del params['outro']
            del params['tests']
            del params['gid']

            try:
                params = bson.json_util.dumps(params)
            except Exception as e:
                self.logger.exception(e)
                return bson.json_util.dumps({'status': 'error', 'message': e})

            res = self.kk.postRequest("/issue", data=params, **kwargs)
            if res['status'] == 'success':
                self.logger.info("Ticket %s created!", res['data']['issue'])
                # mark as ticketed
                query = {'_id': {"$in": testIds}}
                updoc = {"$set": {'ticket': {'key': res['data']['issue'],
                                             'ts': datetime.now()}}}
                self.coll_failedtests.update(query, updoc, multi=True)
            else:
                self.logger.warning(res['message'])
                return bson.json_util.dumps({'status': 'error',
                                             'message': res['message']})
            return bson.json_util.dumps(res)

        @b.post('/previewissue')
        @tokenize
        def preview_issue(**kwargs):
            params = json.load(bottle.request.body)
            renderedTicket = render_issue_description(params)
            return bson.json_util.dumps({"status": "success", "data": renderedTicket})

        @b.route('/tasks')
        @tokenize
        def issue_summary(**kwargs):
            # list of workflows
            res = self.kk.workflowRequest(**kwargs)
            if res['status'] != "success":
                return bottle.template('base_page', error=res['message'],
                                       renderpage="tasks")
            else:
                workflows = res['data']['workflows']

            workflowMap = {workflow['name']: workflow for workflow in
                           workflows}
            workflowNames = workflowMap.keys()
            workflowNames.sort()

            user_workflows = []
            cookie_workflowNames = bottle.request.get_cookie('workflows')

            # convert the octal
            if cookie_workflowNames:
                cookie_workflowNames = urlparse.unquote(cookie_workflowNames)
                if cookie_workflowNames and cookie_workflowNames != "[]":
                    try:
                        user_workflows = bson.json_util.\
                            loads(cookie_workflowNames)
                        user_workflows.sort()
                    except Exception as e:
                        self.logger.exception(e)

            content = ''
            for workflow in user_workflows:
                content += get_rendered_workflow(workflow, **kwargs)
            return bottle.template(
                'base_page', renderpage="tasks",
                allWorkflows=workflowNames, content=content)

        @b.route('/task/<task>/process')
        @tokenize
        def process_task(task, **kwargs):
            return response(self.kk.taskRequest(task, "process", **kwargs))

        @b.route('/task/<task>/approve')
        @tokenize
        def approve_task(task, **kwargs):
            self.kk.taskRequest(task, "approve")
            return response(self.kk.taskRequest(task, "approve", **kwargs))

        @b.route('/task/<task>/disapprove')
        @tokenize
        def disapprove_task(task, **kwargs):
            return response(self.kk.taskRequest(task, "disapprove", **kwargs))

        @b.route('/task/<task>/remove')
        @tokenize
        def remove_task(task, **kwargs):
            return response(self.kk.taskRequest(task, "remove", **kwargs))

        @b.route('/task/<task>/sleep')
        @tokenize
        def freeze_task(task, **kwargs):
            return response(self.kk.taskRequest(task, "sleep", **kwargs))

        @b.route('/task/<task>/wake')
        @tokenize
        def wake_task(task, **kwargs):
            return response(self.kk.taskRequest(task, "wake", **kwargs))

        @b.route('/task/<task>/sleep/<seconds>')
        @tokenize
        def sleep_task(task, seconds, **kwargs):
            seconds = int(seconds)
            return response(self.kk.taskRequest(task, "sleep", seconds,
                                                **kwargs))

        @b.post('/user/<uid>/workflow/<workflow>')
        @tokenize
        def user_add_workflow(uid, workflow, **kwargs):
            """ Add user workflow """
            res = self.kk.postRequest("/user/%s/workflow/%s" % (uid, workflow),
                                      **kwargs)
            return bson.json_util.dumps(res)

        @b.delete('/user/<uid>/workflow/<workflow>')
        @tokenize
        def user_remove_workflow(uid, workflow, **kwargs):
            """ Remove user workflow """
            res = self.kk.deleteRequest("/user/%s/workflow/%s" % (uid,
                                        workflow), **kwargs)
            return bson.json_util.dumps(res)

        @b.route('/workflows')
        @tokenize
        def edit_workflows(**kwargs):
            databases = {}
            for name in self.mongo.database_names():
                databases[name] = self.mongo[name].collection_names()
            return bottle.template('base_page', renderpage="workflows",databases=databases)

        @b.post('/testworkflow')
        @tokenize
        def test_workflow(**kwargs):
            formcontent = bottle.request.body.read()
            if 'workflow' in formcontent:
                workflow = bson.json_util.loads(formcontent)['workflow']
                wfstring = bson.json_util.dumps(workflow)
                res = self.kk.postRequest("/testworkflow", data=wfstring,
                                          **kwargs)
                if res['status'] == "success":
                    ns = res['data']['ns']
                    docs = res['data']['docs']
                    for doc in docs:
                        if ns == "support.issues":
                            if 'changelog' in doc['jira']:
                                del doc['jira']['changelog']
                            if 'fields' in doc['jira'] and 'comment' in\
                                    doc['jira']['fields']:
                                del doc['jira']['fields']['comment']
                            if 'fields' in doc['jira'] and 'attachment' in\
                                    doc['jira']['fields']:
                                del doc['jira']['fields']['attachment']
                            if 'karakuri' in doc and 'sleep' in\
                                    doc['karakuri']:
                                del doc['karakuri']['sleep']
                    return bson.json_util.dumps(res)
                else:
                    return bson.json_util.dumps(res)
            msg = {"status": "error",
                   "message": "workflow missing 'query_string'"}
            return bson.json_util.dumps(msg)

        @b.post('/workflow')
        @tokenize
        def create_workflow(**kwargs):
            formcontent = bottle.request.body.read()
            workflow = bson.json_util.loads(formcontent)['workflow']
            wfstring = bson.json_util.dumps(workflow)
            return self.kk.postRequest("/workflow", data=wfstring, **kwargs)

        @b.post('/workflow/<wfname>')
        @tokenize
        def update_workflow(wfname, **kwargs):
            formcontent = bottle.request.body.read()
            workflow = bson.json_util.loads(formcontent)['workflow']
            workflow_id = bson.json_util.ObjectId(workflow['_id'])
            workflow['_id'] = workflow_id
            wfstring = bson.json_util.dumps(workflow)
            return self.kk.postRequest("/workflow", entity=wfname,
                                       data=wfstring, **kwargs)

        @b.delete('/workflow/<wfname>')
        @tokenize
        def delete_workflow(wfname, **kwargs):
            return self.kk.deleteRequest("/workflow", entity=wfname, **kwargs)

        @b.route('/workflow')
        @b.route('/workflow/')
        @tokenize
        def get_workflow(**kwargs):
            return response(self.kk.workflowRequest(**kwargs))

        @b.route('/workflow/<name>/rendered')
        @tokenize
        def get_rendered_workflow(name, **kwargs):
            res = self.kk.workflowRequest(name, 'queue', **kwargs)
            if res['status'] == "success":
                task_summary = res['data']
            else:
                task_summary = []

            issue_objs = {}
            res = self.kk.workflowRequest(name, 'issuesummaries', **kwargs)
            issues = None
            if res['status'] == "success":
                issues = res['data']
            if issues is not None:
                for issue in issues['issues']:
                    issue_objs[str(issue['_id'])] = issue['jira']

            if (task_summary is not None and
                    'tasks' in task_summary and
                    len(task_summary['tasks']) > 0):
                for task in task_summary['tasks']:
                    if 'start' in task:
                        task['startDate'] = task['start'].\
                            strftime("%Y-%m-%d %H:%M")
                        starttz = task['start'].tzinfo
                        end_of_time = utc.localize(datetime.max).\
                            astimezone(starttz)
                        end_of_time_str = end_of_time.\
                            strftime("%Y-%m-%d %H:%M")
                        if task['startDate'] == end_of_time_str:
                            task['frozen'] = True
                        else:
                            task['frozen'] = False
                    else:
                        task['startDate'] = ""
                        task['frozen'] = False
                    task['updateDate'] = task['t'].\
                        strftime(format="%Y-%m-%d %H:%M")

            hidden_done = {}
            cookie_hideDone = bottle.request.get_cookie('workflows_hide_done')
            # convert the octal
            if cookie_hideDone:
                cookie_hideDone = urlparse.unquote(cookie_hideDone)
                if cookie_hideDone and cookie_hideDone != "[]":
                    try:
                        tmp = bson.json_util.loads(cookie_hideDone)
                        for i in tmp:
                            hidden_done[i] = 1
                    except Exception as e:
                        self.logger.exception(e)
            if name in hidden_done:
                hide_done = True
            else:
                hide_done = False

            hidden_frozen = {}
            cookie_hideFrozen = bottle.request.\
                get_cookie('workflows_hide_frozen')
            # convert the octal
            if cookie_hideFrozen:
                cookie_hideFrozen = urlparse.unquote(cookie_hideFrozen)
                if cookie_hideFrozen and cookie_hideFrozen != "[]":
                    try:
                        tmp = bson.json_util.loads(cookie_hideFrozen)
                        for i in tmp:
                            hidden_frozen[i] = 1
                    except Exception as e:
                        self.logger.exception(e)
            if name in hidden_frozen:
                hide_frozen = True
            else:
                hide_frozen = False

            data = {'ticketSummary': task_summary, 'issues': issue_objs,
                    'hide_done': hide_done, 'hide_frozen': hide_frozen}
            return response(self.kk.workflowRequest(name, **kwargs),
                            template="tasks_workflow", template_data=data)

        @b.route('/workflow/<workflow>/process')
        @tokenize
        def process_workflow(workflow, **kwargs):
            return response(self.kk.workflowRequest(workflow, "process",
                                                    **kwargs))

        @b.route('/workflow/<workflow>/approve')
        @tokenize
        def approve_workflow(workflow, **kwargs):
            return response(self.kk.workflowRequest(workflow, "approve",
                                                    **kwargs))

        @b.route('/workflow/<workflow>/disapprove')
        @tokenize
        def disapprove_workflow(workflow, **kwargs):
            return response(self.kk.workflowRequest(workflow, "disapprove",
                                                    **kwargs))

        @b.route('/workflow/<workflow>/remove')
        @tokenize
        def remove_workflow(workflow, **kwargs):
            return response(self.kk.workflowRequest(workflow, "remove",
                                                    **kwargs))

        @b.route('/workflow/<workflow>/sleep/<seconds>')
        @tokenize
        def sleep_workflow(workflow, seconds, **kwargs):
            return response(self.kk.workflowRequest(workflow, "sleep", seconds,
                                                    **kwargs))

        # UPLOAD-RELATED ROUTES
        @b.route('/mdiag')
        def mdiag_form():
            return bottle.template('base_page', renderpage="mdiag")

        @b.route('/mdiag/ticketinfo/<jira_key>')
        def mdiag_ticketinfo(jira_key):
            results = md.getTicketInfo(jira_key)
            return bson.json_util.dumps(results)

        @b.post('/mdiag/upload')
        def mdiag_upload_files():
            jira_key = bottle.request.forms.get('jiraid')
            upload = bottle.request.files.get('file')
            name, ext = os.path.splitext(upload.filename)
            self.logger.info(jira_key)
            self.logger.info(upload.filename)
            content = upload.file.read()

            # if ext not in ('.zip', '.json', '.gzip'):
            if ext != '.json':
                print 'File extension not allowed.'
                return False
            return md.processMdiagFile(content, jira_key)

        # AUTOCOMPLETE SEARCH
        @b.route('/search/<query>')
        def autocomplete(query):
            results = []
            if query is not None:
                results = g.search(query)
            return bson.json_util.dumps(results)

        # STATIC FILES
        @b.route('/js/<filename>')
        def server_js(filename):
            return bottle.static_file(filename, root="%s/js" %
                                      self.args['root_webdir'])

        @b.route('/css/<filename>')
        def server_css(filename):
            return bottle.static_file(filename, root="%s/css" %
                                      self.args['root_webdir'])

        @b.route('/img/<filename>')
        def server_img(filename):
            return bottle.static_file(filename, root="%s/img" %
                                      self.args['root_webdir'])

        @b.route('/kibana')
        @b.route('/kibana/')
        def kibana_index():
            return bottle.redirect('/kibana/index.html')

        @b.route('/kibana/<filepath:path>')
        def server_kibana(filepath):
            return bottle.static_file(filepath, root="%s/kibana" %
                                      self.args['root_webdir'])

        self.logger.debug("start()")
        self.logger.info("euphonia!")

        b.run(host=self.args['euphonia_host'], port=self.args['euphonia_port'])

if __name__ == "__main__":
    desc = "A euphoric experience"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument("--euphonia-host", metavar="HOST",
                               default="localhost",
                               help="specify the euphonia host "
                                    "(default=localhost)")
    parser.add_config_argument("--euphonia-port", metavar="PORT", type=int,
                               default=8070,
                               help="specify the euphonia port (default=8080)")
    parser.add_config_argument("--karakuri-host", metavar="HOST",
                               default="localhost",
                               help="specify the karakuri host "
                                    "(default=localhost)")
    parser.add_config_argument("--karakuri-port", metavar="PORT", type=int,
                               default=8080,
                               help="specify the karakuri port "
                                    "(default=8080)")
    parser.add_config_argument("--sfdc-password", metavar="SFDCPASSWORD",
                               help="specify a SFDC password")
    parser.add_config_argument("--sfdc-username", metavar="SFDCUSERNAME",
                               help="specify a SFDC username")
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                               "(default=mongodb://localhost:27017)")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/euphonia.pid",
                               help="specify a PID file "
                                    "(default=/tmp/euphonia.pid)")
    parser.add_config_argument("--root-webdir", metavar="DIRECTORY",
                               default="%s/web" % os.getcwd(),
                               help="specify the root web directory")
    parser.add_config_argument("--token", metavar="TOKEN",
                               help="specify a user token to persist")
    # parser.add_config_argument("--sf-password", metavar="PASSWORD",
    #                            help="specify a Salesforce password")
    # parser.add_config_argument("--sf-server", metavar="URL",
    #                            help="specify a Salesforce server URL")
    # parser.add_config_argument("--sf-username", metavar="USERNAME",
    #                            help="specify a Salesforce USERNAME")
    parser.add_argument("command", choices=["start", "stop", "restart",
                                            "debug"],
                        help="<-- the available actions, choose one")
    args = parser.parse_args()

    # Initialize logging
    logging.basicConfig(format='%(asctime)s - %(module)s - %(levelname)s - '
                               '%(message)s')
    logger = logging.getLogger("logger")
    logger.setLevel(args.log_level)

    if args.command == "debug":
        # Running un-daemonized
        e = Euphonia(args)

        # Initialize SFDC++
        try:
            sfdcpp = sfdcpp(args, e.mongo)
            sfdcpp.setLive(True)
            e.setSfdc(sfdcpp)
        except Exception as exc:
            e.logger.exception("Could not load SFDC++")
            e.logger.exception(exc)

        e.start()
        sys.exit(0)

    # Require a log file and preserve it while daemonized
    if args.log is None:
        print("Please specify a log file")
        sys.exit(1)

    # Lock it down
    pidfile = pidlockfile.PIDLockFile(args.pid)

    if args.command == "start":
        if pidfile.is_locked():
            print("There is already a running process")
            sys.exit(2)

    if args.command == "stop":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
            sys.exit(0)
        else:
            print("There is no running process to stop")
            sys.exit(3)

    if args.command == "restart":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
        else:
            print("There is no running process to stop")

    fh = logging.FileHandler(args.log)
    logger.addHandler(fh)

    # This is daemon territory
    context = daemon.DaemonContext(pidfile=pidfile,
                                   stderr=fh.stream, stdout=fh.stream)
    context.files_preserve = [fh.stream]
    # TODO implment signal_map

    with context:
        e = Euphonia(args)

        # Initialize SFDC++
        try:
            sfdcpp = sfdcpp(args, e.mongo)
            sfdcpp.setLive(args.live)
            e.setSfdc(sfdcpp)
        except Exception as exc:
            e.logger.exception("Could not load SFDC++")
            e.logger.exception(exc)

        e.start()
sys.exit(0)
