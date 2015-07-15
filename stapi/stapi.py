#!/usr/bin/env python
"""
# -----------------------------------------------------------------------
# stAPI = SupporT API. This is an interface to all data relevant
# to the MongoDB support team and its applications. All data is
# accessed through a RESTful API interface to the MongoDB
# support database.
#
# TODO: Add authentication so that all sensitive requests and
# DB changes require user authentication
#
# TODO: Make the main API methods static so they don't necessarily have
# to be called from an instace of stAPI. Seems like most of them should
# just be callable from the class
# -----------------------------------------------------------------------
"""

import argumentparserpp
import bottle
import bson
import bson.json_util
import copy
import daemon
import dateutil.parser
import gzip
import logging
import os
import pidlockfile
import pymongo
import review_queue
import signal
import StringIO
import sys
import time

from pprint import pprint
from datetime import datetime, timedelta
# from jirapp import jirapp
# from sfdcpp import sfdcpp
from supportissue import SupportIssue  # , isMongoDBEmail

class stAPI:
    """ A centralized support API that is waiting for a name from Pete... """
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.logger = logging.getLogger("logger")

        self.support_query = {'$and': [
            {'jira.fields.issuetype.name': {'$nin': ['Tracking']}},
            {'jira.fields.project.key': {'$in': ['CS', 'MMSSUPPORT', 'SUPPORT',
                'PARTNER']}}
            ]
        }

        self.dash_proj = {'_id': 0,
            'dash.active.now': 1,
            'deleted': 1,
            'jira.fields.assignee': 1,
            'jira.fields.created': 1,
            'jira.fields.issuetype': 1,
            'jira.fields.summary': 1,
            'jira.fields.labels': 1,
            'jira.fields.priority.id': 1,
            'jira.fields.reporter': 1,
            'jira.fields.status': 1,
            'jira.fields.updated': 1,
            'jira.fields.comment.comments.author.emailAddress': 1,
            'jira.fields.comment.comments.created': 1,
            'jira.fields.comment.comments.updated': 1,
            'jira.fields.comment.comments.visibility': 1,
            'jira.key': 1,
            'jira.tags': 1,
            'sla': 1
        }

        self.jira = None
        self.sfdc = None
        # The issue tracking system
        self.issuer = None

        # Are we hot!? "F**k it! We'll do it live!"
        self.live = self.args['live']

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        """ TODO: Users should either be moved to the support DB or be its
        own DB. It should not reside in the karakuri DB"""
        self.coll_users = self.mongo.karakuri.users
        self.coll_issues = self.mongo.support.issues
        self.coll_companies = self.mongo.support.companies
        self.coll_reviews = self.mongo.support.reviews

        # This the review_queue.py functions created by J-man Wahlin
        self.RQ = review_queue.ReviewQueue(self.mongo.support)

    def find(self, collection, query, proj=None):
        """ Wrapper for find that handles exceptions """
        """NOTE: query is assumed to be in correct format"""
        # self.logger.debug("find(%s,%s,%s)", collection, query, proj)
        try:
            docs = collection.find(query, proj)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': docs}

    def find_and_modify(self, collection, match, updoc, upsert=False, proj={}):
        """ Wrapper for find_and_modify that handles exceptions """
        self.logger.debug("find_and_modify(%s,%s,%s)", collection, match,
                          updoc)
        try:
            # return the 'new' updated document
            doc = collection.find_one_and_update(match, updoc, upsert=upsert,
                projection=proj, return_document=ReturnDocument.AFTER)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': doc}

    def find_and_modify_issue(self, match, updoc):
        """ find_and_modify for support.issues that automatically updates the
        'updated' timestamp """
        self.logger.debug("find_and_modify_issue(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['updated'] = datetime.utcnow()
        else:
            updoc["$set"] = {'updated': datetime.utcnow()}
        return self.find_and_modify(self.coll_issues, match, updoc)

    def find_one(self, collection, match):
        """ Wrapper for find_one that handles exceptions """
        self.logger.debug("find_one(%s,%s)", collection, match)
        try:
            doc = collection.find_one(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': doc}

    def addReviewer(self, id, reviewer, **kwargs):
        """ Add a reviewer to the given review """
        self.logger.debug("addReviewer(%s, %s)" % (id, reviewer))

        add_rev_req = {'action': 'add_reviewer'}
        add_rev_req['review_id'] = id
        add_rev_req['reviewer'] = reviewer
        try:
            self.RQ.add_reviewer(add_rev_req)
            res = {"ok": True, "payload": {"id": id, "added reviewer": reviewer}}
        except Exception as e:
            res = {"ok": False, "payload": e}

        # match = {"key": id}
        # updoc = {"reviewer": }
        # proj = {"_id": 0, "key": 1, "done": 1, "requested_by": 1,
        #         "reviewers": 1, "lgtms": 1
        #         }
        # res = self.find_and_modify(self.coll_reviews, match, proj, )

        if not res['ok']:
            return res
        result = res['payload']

        if result is None:
            message = "Something went wrong in addReviewer. Result is None."
            self.logger.warning(message)
            return {"ok": False, "payload": message}
        return {'ok': True, 'payload': result}

    def addlooking(self, id, looker, **kwargs):
        """ Add a looking to the given review """
        self.logger.debug("addlooking(%s, %s)" % (id, looker))

        req = {'action': 'add_looking'}
        req['review_id'] = id
        req['lookin'] = looking
        try:
            self.RQ.add_looking(req)
            res = {"ok": True, "payload": {"id": id, "added looking": looking}}
        except Exception as e:
            res = {"ok": False, "payload": e}

        # match = {"key": id}
        # updoc = {"reviewer": }
        # proj = {"_id": 0, "key": 1, "done": 1, "requested_by": 1,
        #         "reviewers": 1, "lgtms": 1
        #         }
        # res = self.find_and_modify(self.coll_reviews, match, proj, )

        if not res['ok']:
            return res
        result = res['payload']

        if result is None:
            message = "Something went wrong in addLooking. Result is None."
            self.logger.warning(message)
            return {"ok": False, "payload": message}
        return {'ok': True, 'payload': result}

    def removelooking(self, id, looker, **kwargs):
        """ Remove a looker from the given review """
        self.logger.debug("removelooking(%s, %s)" % (id, looker))

        req = {'action': 'remove_looking'}
        req['review_id'] = id
        req['looker'] = looker
        try:
            self.RQ.remove_looking(req)
            res = {"ok": True, "payload": {"id": id, "removed looking": looker}}
        except Exception as e:
            res = {"ok": False, "payload": e}

        if not res['ok']:
            return res
        result = res['payload']

        if result is None:
            message = "Something went wrong in addLooking. Result is None."
            self.logger.warning(message)
            return {"ok": False, "payload": message}
        return {'ok': True, 'payload': result}

    def removeReviewer(self, id, reviewer, **kwargs):
        """ Remove a reviewer from the given review """
        self.logger.debug("removeReviewer(%s, %s)" % (id, reviewer))

        rem_rev_req = {'action': 'remove_reviewer'}
        rem_rev_req['review_id'] = id
        rem_rev_req['reviewer'] = reviewer
        try:
            self.RQ.remove_reviewer(rem_rev_req)
            res = {"ok": True, "payload": {"id": id, "removed reviewer": reviewer}}
        except Exception as e:
            res = {"ok": False, "payload": e}

        if not res['ok']:
            return res
        result = res['payload']

        if result is None:
            message = "Something went wrong in removeReviewer. Result is None."
            self.logger.warning(message)
            return {"ok": False, "payload": message}
        return {'ok': True, 'payload': result}

    def createUser(self, user, **kwargs):
        """ Create a new user with appropriate defaults """
        self.logger.debug("createUser(%s)", user)

        match = {'user': user}
        updoc = {'groups': [],
                 'name': '"A man needs a name..."',
                 'token_created_date': datetime.now(),
                 'token_expiry_date': datetime.max,
                 'workflows': ["MyOpenTickets"]}
        # third argument is upsert
        return self.find_and_modify_user(match, updoc, True)

    def getIssues(self, query, proj=None, **kwargs):
        """ Return all issues from query """
        self.logger.debug("getIssues()")

        res = self.find(self.coll_issues, query, proj)

        if not res['ok']:
            return res
        docs = res['payload']

        if docs is None:
            message = "No active issues"
            self.logger.warning(message)
        return {'ok': True, 'payload': docs}

    def getActiveReviews(self, **kwargs):
        """ Return all active reviews """
        self.logger.debug("getActiveReviews()")

        res = self.find(self.coll_reviews, {"done": False})
        if not res['ok']:
            return res
        docs = res['payload']

        if docs is None:
            message = "No active reviews"
            self.logger.warning(message)
        return {'ok': True, 'payload': docs}

    def getActiveUNAs(self, **kwargs):
        """ Return FTSs  """
        self.logger.debug("getActiveUNAs()")

        if kwargs.get('query', None) is not None:
            query = kwargs.get('query', None)
        else:
            query = {'$and': [{}]}

        query['$and'].append({'jira.fields.status.name':
                            {'$in': ['Open', 'Reopened',
                                    'In Progress',
                                    'Waiting For User Input']}})
        query['$and'].append({'jira.fields.assignee': None})

        proj = kwargs.get('proj', None)

        res = self.find(self.coll_issues, query, proj)

        if not res['ok']:
            return res
        docs = res['payload']

        unas = []
        for doc in docs:
            issue = SupportIssue().fromDoc(doc)

            if self._isUNA(issue):
                unas.append(doc)

        return {'ok': True, 'payload': unas}

    def getIssueByID(self, **kwargs):
        """ Return issue for the given iid """
        iid = kwargs.get('id', None)
        self.logger.debug("getIssueByID(%s)", iid)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        res = self.find_one(self.coll_issues, {'_id': iid})
        if not res['ok']:
            return res
        doc = res['payload']

        if doc is None:
            message = "issue %s not found" % iid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': doc}

    def getUserByToken(self, token, **kwargs):
        """ Return the associated user document """
        self.logger.debug("getUserByToken(%s)", token)
        # Currently authenticating against username
        # TODO: use Crowd REST API to validate token
        res = self.find_one(self.coll_users, {'user': token})
        if not res['ok']:
            return res
        user = res['payload']

        if user is None:
            message = "user not found for token '%s'" % token
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': user}

    """ Return a JSON-validated dict for the string """
    def _loadJson(self, string):
        self.logger.debug("loadJson(%s)", string)
        try:
            res = bson.json_util.loads(string)
        except Exception as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': res}

    def _isSLA(self, issue):
        """Return true if the issue should be displayed in the SLA row of the
        dashboard."""
        return (issue.isActive() and
                issue.hasSLA() and
                'expireAt' in issue.doc['sla'] and
                issue.doc['sla']['expireAt'] is not None and
                ((not issue.isProactive() and
                    issue.firstXGenPublicComment is None)
                    or (issue.isProactive() and
                        issue.firstXGenPublicCommentAfterCustomerComment
                            is None)))

    def _isFTS(self, issue):
        """Return true if the issue should be displayed in the FTS row of the
        dashboard."""
        return (issue.isActive() and
                issue.isFTS())

    def _isUNA(self, issue):
        """Ticket qualifies as UNA if it is open, not an SLA, and has
        no assignee. Simple"""
        assignee = issue.doc["jira"]["fields"]["assignee"]
        if issue.lastXGenPublicComment is None and issue.hasSLA():
            # Will show up as an SLA
            return False
        elif issue.status in ("Resolved", "Closed", "Waiting for bug fix",
                              "Waiting for Feature", "Waiting for Customer"):
            return False
        return (issue.isActive() and assignee is None)

    # ----------------------------------------------------
    # Set the ticketing system to include one of the
    # issue aggregators, null by default.
    # ----------------------------------------------------

    # def updateIssue(self, iid, updoc, **kwargs):
    #     """ They see me rollin' """
    #     """ ** They see me mowin' my front lawn """
    #     self.logger.debug("updateIssue(%s,%s)", iid, updoc)
    #     res = self.getObjectId(iid)
    #     if not res['ok']:
    #         return res
    #     iid = res['payload']
    #     match = {'_id': iid}
    #     return self.find_and_modify_issue(match, updoc)

    def start(self):
        """ Start the RESTful interface """
        self.logger.debug("start()")
        self.logger.info("stAPI is at REST")

        b = bottle.Bottle(autojson=False)

        def authenticated(func):
            """ A decorator for bottle-route callback functions that require
            authentication """
            def wrapped(*args, **kwargs):
                # Determine whether or not I am allowed to execute this action
                header = bottle.request.get_header('Authorization')
                if not header:
                    bottle.abort(401)
                keyValuePairs = [kv for kv in [keyValue.split('=') for keyValue
                                               in header.split(',')]]
                auth_dict = {}
                for kv in keyValuePairs:
                    if len(kv) == 2:
                        auth_dict = {kv[0]: kv[1]}
                token = auth_dict.get('usr_token', None)
                match = {'user': token}
                doc = self.coll_users.find_one(match)
                if not doc:
                    bottle.abort(401)
                else:
                    kwargs['userDoc'] = doc
                    return func(*args, **kwargs)
            return wrapped

        @b.hook('before_request')
        def checkAndSetAccessControlAllowOriginHeader():
            if self.args['access_control_allowed_origins'] is not None:
                allowed_origins = self.args['access_control_allowed_origins']\
                                      .split(',')
                origin = bottle.request.get_header('Origin')
                if origin in allowed_origins:
                    bottle.response.set_header('Access-Control-Allow-Origin',
                                               origin)

        def success(data=None):

            logger.debug("Time to start of success() : " +
                str(time.time() % 10) + "\n")

            ret = {'status': 'success', 'data': data}

            bottle.response.status = 200
            bottle.response.add_header("Content-Encoding", "gzip")

            logger.debug("Time to before issues_list : " +
                str(time.time() % 10) + "\n")

            content = bson.json_util.dumps(ret)

            logger.debug("Time to after bson dump : " +
                str(time.time() % 10) + "\n")

            compressed = StringIO.StringIO()

            logger.debug("Time to after iteration : " +
                str(time.time() % 10) + "\n")

            with gzip.GzipFile(fileobj=compressed, mode='w') as f:
                f.write(content)

            logger.debug("Time to after gzip compress : " +
                str(time.time() % 10) + "\n")

            temp = compressed.getvalue()

            logger.debug("Time to just after compressed.getvalue() : " +
                str(time.time() % 10) + "\n")

            return temp

        def fail(data=None):
            ret = {'status': 'fail', 'data': data}
            bottle.response.status = 403
            return bson.json_util.dumps(ret)

        def error(message=None):
            ret = {'status': 'error', 'message': str(message)}
            bottle.response.status = 403
            return bson.json_util.dumps(ret)

        def _response(method, **kwargs):
            res = method(**kwargs)
            if res['ok']:
                return success(res['payload'])
            return error(res['payload'])

        # -------------------------------------------------------------
        # Endpoints of the RESTful API
        # -------------------------------------------------------------

        @b.get('/login')
        def user_login(**kwargs):
            """ Find a user with the specified auth_token """
            self.logger.debug("user_login()")
            token = bottle.request.params.get('token')
            if token:
                token = token.replace('%40', '@')
                res = self.getUserByToken(token)
                if not res['ok']:
                    # a new user, hooray!?
                    res = self.createUser(token)
                    if not res['ok']:
                        return error(res['payload'])
                user = res['payload']

                if user is not None:
                    return success(res['payload'])
            return error("unable to authenticate token")

        @b.post('/issues')
        @authenticated
        def issue_create(**kwargs):
            body = bottle.request.body.read()

            res = self._loadJson(body)  # move loadJson() to common lib
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.createIssue(fields, **kwargs)
            if res['ok']:
                return success({'issue': res['payload']})
            return error(res['payload'])

        @b.route('/reviews')
        @authenticated
        def active_reviews(**kwargs):
            # """Returns all active reviews"""
            if bottle.request.query.get('active', None) is not None:
                return _response(self.getActiveReviews, **kwargs)
            else:
                return _response(self.get, self.coll_reviews,
                                    query={}, **kwargs)

        @b.route('/reviews/<id>')
        @authenticated
        def review_id(id, **kwargs):
            return _response(self.getReviewByID, id=id, **kwargs)

        @b.route('/reviews/<id>/reviewer/self')
        @authenticated
        def reviewer_self(id, **kwargs):
            reviewer = kwargs['userDoc']['name']
            return _response(self.addReviewer, id=id, reviewer=reviewer, **kwargs)

        @b.route('/reviews/<id>/looking/self')
        @authenticated
        def looking_self(id, **kwargs):
            looker = kwargs['userDoc']['name']
            return _response(self.addlooking, id=id, looker=looker, **kwargs)

        @b.route('/reviews/<id>/unlooking/self')
        @authenticated
        def unlooking_self(id, **kwargs):
            looker = kwargs['userDoc']['name']
            return _response(self.removelooking, id=id, looker=looker, **kwargs)

        @b.route('/reviews/<id>/unreview/self')
        @authenticated
        def unreview_self(id, **kwargs):
            reviewer = kwargs['userDoc']['name']
            return _response(self.removeReviewer, id=id, reviewer=reviewer, **kwargs)

        @b.route('/issues/<id>')
        @authenticated
        def issue_id(id, **kwargs):
            return _response(self.getIssueByID, id=id, **kwargs)

        @b.route('/issues/summary/sla')
        @authenticated
        def issues_sla(**kwargs):
            proj = self.dash_proj
            query = copy.deepcopy(self.support_query)
            query['$and'].append({'jira.fields.status.name': 'Open'})
            query['$and'].append({'sla.expireAt': {'$ne': None}})

            res = self.getIssues(query, proj, **kwargs)
            if not res['ok']:
                return error(res['payload'])
            else:
                docs = res['payload']

            data = []
            for i in docs:
                issue = SupportIssue().fromDoc(i)
                if self._isSLA(issue):
                    data.append(i)
            return success(data)

        @b.route('/issues/summary/fts')
        @authenticated
        def issues_fts(**kwargs):
            proj = self.dash_proj
            query = copy.deepcopy(self.support_query)
            query['$and'].append({
                'jira.fields.status.name': {'$in': [
                    'Open', 'Reopened', 'In Progress',
                    'Waiting For User Input']}})
            query['$and'].append({'jira.fields.labels': 'fs'})

            res = self.getIssues(query, proj, **kwargs)
            if not res['ok']:
                return error(res['payload'])
            else:
                docs = res['payload']

            data = []
            for i in docs:
                issue = SupportIssue().fromDoc(i)

                if self._isFTS(issue):
                    data.append(i)
            return success(data)

        """ Return a summary pertaining to the dashboard. The possible query
        parameters are:

        # last_updated: a time to trace updates to,
        # support: filters only issues related to support (CS, MMSSUPPORT, etc)
        # active: active issues
        # una: unassigned issues
        # wait: issues waiting for customer input
        # usr_assigned: all issues assigned to a user name

        and each parameter adds a filter in the query search """
        @b.route('/issues/summary')
        @authenticated
        def dash_issues(**kwargs):
            # Returns a trimmed (projected) set of issues
            proj = self.dash_proj  # added cuz we're in the /dash summary obj

            # If suppprt filter is set, only give back issues related to
            # support
            if bottle.request.query.get('support', None) is not None:
                query = copy.deepcopy(self.support_query)
            else:
                query = {'$and': [{}]}

            last_updated = bottle.request.query.get('last_updated', None)
            if last_updated is not None:
                logger.debug(last_updated)
                logger.debug("that's last updated " + str(last_updated) + "\n")
                last_updated = dateutil.parser.parse(last_updated)
                last_updated = last_updated - timedelta(seconds=30)
                query['and'].append({"jira.fields.updated": {"$gte":
                                                            last_updated}})

            if bottle.request.query.get('active', None) is not None:
                if bottle.request.query.get('wait', None) is not None:
                    query['$and'].append({'jira.fields.status.name': {'$in': [
                                            'Open', 'Reopened',
                                            'In Progress',
                                            'Waiting For User Input',
                                            'Waiting For Customer']}})
                else:
                    query['$and'].append({'jira.fields.status.name': {'$in': [
                                            'Open', 'Reopened',
                                            'In Progress',
                                            'Waiting For User Input']}})
                    query['$and'].append({'dash.active.now': True})
            elif bottle.request.query.get('wait', None) is not None:
                query['$and'].append({'jira.fields.status.name':
                                        'Waiting for Customer'})

            if bottle.request.query.get('una', None) is not None:
                query['$and'].append({'jira.fields.assignee': None})

            if bottle.request.query.get('usr_assigned', None) is not None:
                usr_name = kwargs['userDoc']['user']
                self.logger.debug(usr_name)
                self.logger.debug("here " + str(usr_name) + "\n ")
                if usr_name is None:
                    return {'ok': False, 'payload':
                                        'Could not find usr_name in kwargs'}
                query['$and'].append({'jira.fields.assignee.name': usr_name})

            return _response(self.getIssues, query=query, proj=proj,
                **kwargs)

        b.run(host=self.args['rest_host'], port=self.args['rest_port'])

if __name__ == "__main__":
    desc = "An API for all read/write access to the suppport database"

    if os.path.isfile("stapi.log"):
        os.remove("stapi.log")

    parser = argumentparserpp.CliArgumentParser(description=desc)

    parser.add_config_argument("--jira-password", metavar="PASSWORD",
                               help="specify a JIRA password")
    parser.add_config_argument("--jira-username", metavar="USERNAME",
                               help="specify a JIRA username")
    parser.add_config_argument("--live", action="store_true",
                               help="do what you do irl")
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                                    "(default=mongodb://localhost:27017)")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/karakuri.pid",
                               help="specify a PID file "
                                    "(default=/tmp/karakuri.pid)")
    parser.add_config_argument("--rest-host",  metavar="HOST",
                               default="localhost",
                               help="the RESTful interface host "
                               "(default=localhost)")
    parser.add_config_argument("--rest-port",  metavar="PORT", default=8080,
                               type=int,
                               help="the RESTful interface port "
                                    "(default=8080)")
    parser.add_config_argument("--access-control-allowed-origins",
                               metavar="HOSTPORT",
                               help="comma separated list of origins allowed "
                                    "access control")
    parser.add_argument("command", choices=["start", "stop", "restart",
                                            "debug"],
                        help="<-- the available actions, choose one")
    args = parser.parse_args()

    # Require a JIRA login for the time being
    if not args.jira_username or not args.jira_password:
        print("Please specify a JIRA username and password")
        sys.exit(1)

    # Initialize logging
    logging.basicConfig(format='%(asctime)s - %(module)s - %(levelname)s - '
                               '%(message)s')
    logger = logging.getLogger("logger")
    logger.setLevel(args.log_level)

    if args.command == "debug":
        # Running un-daemonized
        s = stAPI(args)

        # Initialize JIRA++
        """commented this out for now. obv come back to it later"""
        # jirapp = jirapp(args.jira_username, args.jira_password, s.mongo)
        # jirapp.setLive(args.live)
        # s.setJira(jirapp)

        # Set the Issuer. There can be only one:
        # https://www.youtube.com/watch?v=sqcLjcSloXs

        # s.setIssuer(jirapp)

        # Keep it going, keep it going, keep it going full steam
        # Intergalactic Planetary
        s.start()
        sys.exit(0)

    # Require a log file and preserve it while daemonized
    if args.log is None:
        print("Please specify a log file")
        sys.exit(2)

    fh = logging.FileHandler(args.log)
    logger.addHandler(fh)

    # Lock it down
    pidfile = pidlockfile.PIDLockFile(args.pid)

    if args.command == "start":
        if pidfile.is_locked():
            print("There is already a running process")
            sys.exit(3)

    if args.command == "stop":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
            sys.exit(4)
        else:
            print("There is no running process to stop")
            sys.exit(5)

    if args.command == "restart":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
        else:
            print("There is no running process to stop")

    # This is daemon territory
    context = daemon.DaemonContext(pidfile=pidfile,
                                   stderr=fh.stream, stdout=fh.stream)
    context.files_preserve = [fh.stream]
    # TODO implment signal_map

    print("Starting...")

    with context:
        s = stAPI(args)

        # Initialize JIRA++
        # jirapp = jirapp(args.jira_username, args.jira_password, s.mongo)
        # jirapp.setLive(args.live)
        # s.setJira(jirapp)

        # Set the Issuer. There can be only one:
        # https://www.youtube.com/watch?v=sqcLjcSloXs
        # TODO cli logic to select the Issuer
        # k.setIssuer(jirapp)

        # Keep it going, keep it going, keep it going full steam
        # Intergalactic Planetary
        s.start()
sys.exit(0)
