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
import isodate
import logging
import os
import pidlockfile
import pymongo
import re
import signal
import string
import StringIO
import sys
import time
import urllib

from datetime import datetime, timedelta
from jirapp import jirapp
from sfdcpp import sfdcpp
from supportissue import SupportIssue, isMongoDBEmail
from ses_handler import SESHandler

class stAPI:
    """ A centralized support API that is waiting for a name from Pete... """
    def __init__(self, args):
    	if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.logger = logging.getLogger("logger")

        self.dash_query = {'$and': [
            {'jira.fields.issuetype.name': {'$nin': ['Tracking']}},
            {'jira.fields.project.key': {'$in': ['CS', 'MMSSUPPORT', 'SUPPORT',
                'PARTNER']}}
            ]
        }

        self.summary_proj = {'_id': 0,
            'dash.active.now': 1,
            'deleted': 1,
            'jira.fields.assignee': 1,
            'jira.fields.created': 1,
            'jira.fields.issuetype': 1,
            'jira.fields.summary': 1,
            'jira.fields.labels': 1,
            'jira.fields.priority.id': 1,
            # 'jira.fields.reporter': 1,
            'jira.fields.status': 1,
            'jira.fields.updated': 1,
            'jira.fields.comment.comments.author.emailAddress': 1,
            'jira.fields.comment.comments.created': 1,
            'jira.fields.comment.comments.updated': 1,
            'jira.fields.comment.comments.visibility': 1,
            'jira.key': 1,
            'jira.tags': 1,
            'sla': 1,
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

    def createIssue(self, fields, **kwargs):
        """ Create a new issue """
        self.logger.debug("createIssue(%s)", fields)

        # ------ Not entirely sure what this callbacks feature is ------ #
        # callbacks = None
        # if 'karakuri' in fields and fields['karakuri'] is not None:
        #     # These arguments are for us, not the ticket
        #     callbacks = copy.deepcopy(fields['karakuri'])
        #     del fields['karakuri']
        # -------------------------------------------------------------- #
        fields = SupportIssue(fields).getJIRAFields()
        res = self.issuer.createIssue(fields)
        if not res['ok']:
            return res
        key = res['payload']
        self.logger.info("Created issue %s", key)
        # Execute callbacks if there are any

        # ------ More callback shtuff ---------------------------------- #
        # if callbacks is not None:
        #     for cb in callbacks:
        #         # Add developer comment to newly created ticket if specified
        #         if 'addDeveloperComment' in cb and\
        #                 cb['addDeveloperComment'] is not None:
        #             res1 = self.issuer.\
        #                 addDeveloperComment(key, cb['addDeveloperComment'])
        #             if not res1['ok']:
        #                 # Not returning on failure because the caller expects
        #                 # an issue key if the issue was created. That's more
        #                 # important than the result of this addDeveloperComment
        #                 # action
        #                 self.logger.\
        #                     warning("Failed to add developer comment to %s",
        #                             key)
        # -------------------------------------------------------------- #
        return res

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

    def find_and_modify(self, collection, match, updoc, upsert=False):
        """ Wrapper for find_and_modify that handles exceptions """
        self.logger.debug("find_and_modify(%s,%s,%s)", collection, match,
                          updoc)
        try:
            # return the 'new' updated document
            doc = collection.find_and_modify(match, updoc, upsert=upsert,
                                             new=True)
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

    def getActiveIssues(self, **kwargs):
        """ Return all active issues """
        self.logger.debug("getActiveIssues()")

        if kwargs.get('query', None) is not None:
            query = kwargs.get('query', None)
        else:
            query = {'$and':[{}]}

        query['$and'].append({'jira.fields.status.name': {'$in': ['Open', 'Reopened',
                'In Progress', 'Waiting For User Input']}})

        proj = kwargs.get('proj', None)

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

    def getActiveFTSs(self, **kwargs):
        """ Return FTSs  """
        self.logger.info("getActiveFTSs()")

        if kwargs.get('query', None) is not None:
            query = kwargs.get('query', None)
        else:
            query = {'$and':[{}]}

        query['$and'].append({'jira.fields.status.name': {'$in': ['Open', 'Reopened', 'In Progress', 'Waiting For User Input']}})
        query['$and'].append({'jira.fields.labels':'fs'})
        proj = kwargs.get('proj', None)

        res = self.find(self.coll_issues, query, proj)

        if not res['ok']:
            return res
        docs = res['payload']

        fts = []
        for doc in docs:
            issue = SupportIssue().fromDoc(doc)

            if self._isFTS(issue):
                fts.append(doc)

        return {'ok': True, 'payload': fts}

    def getActiveSLAs(self, **kwargs):
        """ Return unsatisfied SLAs """
        self.logger.debug("getActiveSLAs()")

        if kwargs.get('query', None) is not None:
            query = kwargs.get('query', None)
        else:
            query = {'$and':[{}]}

        query['$and'].append({'jira.fields.status.name': {'$in': ['Open', 'Reopened',
                'In Progress', 'Waiting For User Input']}})
        query['$and'].append({'sla.expireAt' : {'$ne':None}})
        proj = kwargs.get('proj', None)

        res = self.find(self.coll_issues, query, proj)

        if not res['ok']:
            return res
        docs = res['payload']

        slas = []
        for doc in docs:
            issue = SupportIssue().fromDoc(doc)

            if self._isSLA(issue):
                slas.append(doc)

        return {'ok': True, 'payload': slas}

    def getActiveUNAs(self, **kwargs):
        """ Return FTSs  """
        self.logger.debug("getActiveUNAs()")

        if kwargs.get('query', None) is not None:
            query = kwargs.get('query', None)
        else:
            query = {'$and':[{}]}

        query['$and'].append({'jira.fields.status.name': {'$in': ['Open', 'Reopened',
                'In Progress', 'Waiting For User Input']}})
        query['$and'].append({'jira.fields.assignee':None})

        self.logger.info("una query")
        self.logger.info(query)

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

    def getUpdatedIssues(self, last_updated, **kwargs):
        """return issues that have been updated since passed update string"""
        proj = kwargs.get('proj', None)
        if proj is None:
            proj = {}
        query = {'$and': [
            {'jira.fields.issuetype.name': {'$nin': ['Tracking']}},
            {'jira.fields.project.key': {'$in': ['CS', 'MMSSUPPORT', 'SUPPORT',
                'PARTNER']}},
            {"jira.fields.updated": {"$gte": last_updated}}
            ]
        }

        res = self.find(self.coll_issues, query, proj)

        if not res['ok']:
            return res
        docs = res['payload']

        if docs is None:
            message = "No updated issues"
            self.logger.warning(message)
        return {'ok': True, 'payload': docs}

    def _get(self, col, query=None, proj=None, **kwargs):
        """ Return all issues that match the query. If query is in string format, 
        creates a dictionary using bson.json_util library. Same thing for proj, if
        one exists"""

        logger.debug("Time to start of self.get() : " + str(time.time() % 10) + "\n")

        # Set the collection
        if col == "issues":
            collection = self.coll_issues
        elif col == "reviews":
            collection = self.coll_reviews
        elif col == "companies":
            collection = self.coll_companies
        else:
            raise ValueError("Error in stapi.get(): No collection named %s" % col)

        if query is not None:
            if type(query) is str:
            	query = bson.json_util.loads(query)
            elif type(query) is not dict:
                raise TypeError('Error in getIssues(): '
                    'query is of type %s. Requires <dict> or <str>' % str(type(query)))

            # self.logger.debug("get(%s)", bson.json_util.dumps(query))

        if proj is not None:
            if type(proj) is str:
                proj = bson.json_util.loads(proj)
            elif type(proj) is not dict:
                raise TypeError('Error in getIssues(): '
                    'proj is of type %s. Requires <dict> or <str>' % str(type(proj)))

            # self.logger.debug("get(%s)", bson.json_util.dumps(query))

        logger.debug("Time to just before find() : " + str(time.time() % 10) + "\n")

        res = self.find(collection, query, proj)

        ## self.find returns a payload of a pymongo.cursor.Cursor Ojbect

        logger.debug("Time to just after find() : " + str(time.time() % 10) + "\n")

        if not res['ok']:
            return res
        docs = res['payload']

        if docs is None:
            message = "issue for < %s > query not found" % bson.json_util.dumps(query)
            self.logger.warning(message)

        logger.debug("Time to end of self.get() : " + str(time.time() % 10) + "\n")

        return {'ok': True, 'payload': docs}

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
                ((not issue.isProactive() and issue.firstXGenPublicComment is None)
                    or (issue.isProactive() and
                        issue.firstXGenPublicCommentAfterCustomerComment is None)))

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

    def updateIssue(self, iid, updoc, **kwargs):
        """ They see me rollin' """
        """ ** They see me mowin' my front lawn """
        self.logger.debug("updateIssue(%s,%s)", iid, updoc)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']
        match = {'_id': iid}
        return self.find_and_modify_issue(match, updoc)

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

                # match = {'token': token,
                #         'token_expiry_date': {"$gt": datetime.utcnow()}}
                match = {'user': token}
                doc = self.coll_users.find_one(match)
                if not doc:
                    bottle.abort(401)
                else:
                    kwargs['userDoc'] = doc
                    return func(*args, **kwargs)
            return wrapped

        def success(data=None):

            logger.debug("Time to start of success() : " + str(time.time() % 10) + "\n")

            ret = {'status': 'success', 'data': data}

            bottle.response.status = 200
            bottle.response.add_header("Content-Encoding", "gzip")

            logger.debug("Time to before issues_list : " + str(time.time() % 10) + "\n")

            content = bson.json_util.dumps(ret)

            # issues_list = [i for i in data] 

            logger.debug("Time to after issues_list : " + str(time.time() % 10) + "\n")

            # docs = []

            logger.debug("Time to before iteration : " + str(time.time() % 10) + "\n")

            # for i in issues_list:
            #     docs.append(i)

            compressed = StringIO.StringIO()

            logger.debug("Time to after iteration : " + str(time.time() % 10) + "\n")

            with gzip.GzipFile(fileobj=compressed, mode='w') as f:
                f.write(content)

            logger.debug("Time to after gzip compress : " + str(time.time() % 10) + "\n")

            temp = compressed.getvalue()

            logger.debug("Time to just after compressed.getvalue() : " + str(time.time() % 10) + "\n")

            # return docs
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
        #
        # NOTE: I'm leaving in the @authenticated calls in comments for
        # reference when we add them in later
        # -------------------------------------------------------------

        @b.post('/issues')
        # @authenticated
        def issue_create(**kwargs):
            body = bottle.request.body.read()

            res = self._loadJson(body) #loadJson() is being moved to a common lib
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.createIssue(fields, **kwargs)
            if res['ok']:
                return success({'issue': res['payload']})
            return error(res['payload'])

        @b.route('/reviews')
        # @authenticated
        def active_reviews(**kwargs):
        	#"""Returns all active reviews"""
            if bottle.request.query.get('active', None) is not None:
                # self.logger.debug("here 7 \n\n")
                # self.logger.debug(_response(self.getActiveReviews, **kwargs))
                return _response(self.getActiveReviews, **kwargs)
            else:
                return _response(self.get, self.coll_reviews, query={}, **kwargs)

        """ Have yet to implement this guy. TODO: implement the damnt thing """
        # @b.post('/login')
        # def user_login(**kwargs):
        #     """ Find a user with the specified auth_token """
        #     self.logger.debug("user_login()")
        #     token = bottle.request.params.get('kk_token')
        #     if 'kk_token' in bottle.request.params:
        #         token = bottle.request.params['kk_token']
        #         res = self.getUserByToken(token)
        #         if not res['ok']:
        #             # a new user, hooray!?
        #             res = self.createUser(token)
        #             if not res['ok']:
        #                 return error(res['payload'])
        #         user = res['payload']

        #         if user is not None:
        #             return success(res['payload'])
        #     return error("unable to authenticate token")

        @b.route('/reviews/<id>')
        # @authenticated
        def review_id(id, **kwargs):
            return _response(self.getReviewByID, id=id, **kwargs)

        @b.route('/issues/<id>')
        # @authenticated
        def issue_id(id, **kwargs):
            return _response(self.getIssueByID, id=id, query=query, **kwargs)

        @b.route('/issues/summary')
        # @authenticated
        def issues_summary(**kwargs):
            #""" Returns a trimmed (projected) set of issues """
            proj = self.summary_proj
            last_updated = bottle.request.query.get('last_updated', None)

            if bottle.request.query.get('dash', None) is not None:
                query = copy.deepcopy(self.dash_query)
            else:
                query = {'$and':[{}]}

            if bottle.request.query.get('active', None) is not None:
                return _response(self.getActiveIssues, proj=proj, query=query, 
                    **kwargs)

            elif bottle.request.query.get('sla', None) is not None or \
                bottle.request.query.get('SLA', None) is not None:
                return _response(self.getActiveSLAs, proj=proj, query=query, 
                    **kwargs)

            elif bottle.request.query.get('fts', None) is not None or \
                bottle.request.query.get('FTS', None) is not None:
                return _response(self.getActiveFTSs, proj=proj, query=query, 
                    **kwargs)

            elif bottle.request.query.get('una', None) is not None or \
                bottle.request.query.get('UNA', None) is not None:
                return _response(self.getActiveUNAs, proj=proj, query=query, 
                    **kwargs)

            elif last_updated is not None:
                logger.debug(last_updated)
                logger.debug("that's last updated " + str(last_updated) + "\n")
                last_updated = dateutil.parser.parse(last_updated)
                last_updated = last_updated - timedelta(seconds=30)
                return _response(self.getUpdatedIssues, \
                    last_updated=last_updated, proj=proj, query=query, **kwargs)

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
