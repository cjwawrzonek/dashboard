import argumentparserpp
import daemon
from datetime import datetime, timedelta
import dateutil.parser
import bottle
import bson
import bson.json_util
import bson.son
import json
import karakuriclient
import logging
import math
# from models import groups, tests, mdiag
import os
import pidlockfile
import pymongo
import pytz
import re
from sfdcpp import sfdcpp
import signal
import stAPIclient
import string
from supportissue import SupportIssue, isMongoDBEmail
import sys
import time
import urlparse

from pprint import pprint
from wsgiproxy.app import WSGIProxyApp


# Timedelta has a new method in 2.7 that has to be hacked for 2.6
import ctypes as c
_get_dict = c.pythonapi._PyObject_GetDictPtr
_get_dict.restype = c.POINTER(c.py_object)
_get_dict.argtypes = [c.py_object]

# Potentially use this to create timezone relevant times
utc = pytz.UTC


# ---------------------------------------------------------------------------
# Class to run backend of dashboard. Currently working on porting
# its usage over to a centralized support API.
#
# TODO: Check the handling of timestamps no incoming data. The db stores
# data with an additional timezone stamp which I might not deal
# with properly
# ---------------------------------------------------------------------------
class tk421():
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.logger = logging.getLogger('logger')

        # self.kk = karakuriclient.karakuriclient(args)
        # self.sfdc = None

        # Output args for debugging
        self.logger.debug("parsed args:")
        for arg in self.args:
            if "password" in arg or "passwd" in arg or "token" in arg:
                tmp = "[REDACTED]"
            else:
                tmp = self.args[arg]
            self.logger.debug("%s %s" % (arg, tmp))

        self.sc = stAPIclient.stAPIclient(args)

        # self.token = self.args['token']

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        # self.db_euphonia = self.mongo.euphonia
        self.db_support = self.mongo.support
        # self.coll_failedtests = self.db_euphonia.failedtests
        # self.coll_groups = self.db_euphonia.groups
        # self.coll_tests = self.db_euphonia.tests
        self.coll_companies = self.db_support.companies
        self.coll_issues = self.db_support.issues

        self.lastCacheUpdate = None

    def getData(self, view, **kwargs):
        newData = {
            view:{}, 
            'status':'error', 
            'message':'Error: newData never updated'
        }

        if view == "TC":
            viewData = {'SLA':[], 'FTS':[], 'UNA':[]}
            newData['TC']['SLA'] = self.sc.getActiveSLAs(**kwargs)['payload']
            newData['TC']['FTS'] = self.sc.getActiveFTSs(**kwargs)['payload']
            newData['TC']['UNA'] = self.sc.getActiveUNAs(**kwargs)['payload']
            newData = {'status':'success', 'payload':newData}

        elif view == "REVS":
            viewData = {'REV':[]}
            newData['REVS']['REV'] = self.sc.getActiveReviews(**kwargs)['payload']
            newData = {'status':'success', 'payload':newData}

        elif view == "ACTS":
            viewData = {'ACTS':[]}
            newData['ACTS']['ACTS'] = self.sc.getActiveIssues(**kwargs)['payload']
            newData = {'status':'success', 'payload':newData}

        elif view == "WAITS":
            viewData = {'WAIT':[]}
            newData['WAITS']['WAIT'] = self.sc.getWaitingIssues(**kwargs)['payload']
            newData = {'status':'success', 'payload':newData}

        elif view == "USER":
            viewData = {'USERASSIGNED':[],'USERREVIEW':[],'USERREVIEWER':[]}
            newData['USER']['USERASSIGNED'] = self.sc.getAssignedIssues(**kwargs)['payload']
            newData['USER']['USERREVIEW'] = {} # Must implement this api call
            newData['USER']['USERREVIEWER'] = {} # Must implement this api call
            newData = {'status':'success', 'payload':newData}

        elif view == "UNAS":
            viewData = {'UNAS':[]}
            newData['UNAS']['UNAS'] = self.sc.getUNAs(**kwargs)['payload']
            newData = {'status':'success', 'payload':newData}

        if newData['status'] == "error":
            return {'status':'error', 'message':newData['message']}
        else:
            newData = newData['payload']

        for dataType in newData[view]:
            for i in newData[view][dataType]:
                if dataType != "REV":
                    issue = SupportIssue().fromDoc(i)
                    viewData[dataType].append(self.trimmedDoc(issue, dataType))
                else:
                    viewData[dataType].append(self.trimmedDoc(i, dataType))

            """ Sorting should be moved to Javascript, don't you think? """
            self.sortData(viewData[dataType], dataType.upper())
        return viewData

    # ---------------------------------------------------------------------------
    # TRIMMERS (trim issue with extra info into just what's needed to display it)
    # ---------------------------------------------------------------------------

    """ !IMPORTANT! - I haven't perfectly worked out trimming on the tickets yet.
    What determines the time that appears on the ticket? Right now I just
    have a general trimming method for all issues that aren't SLAs, 
    FTSs, or REVs. This obviously needs to change. """

    def trimmedDoc(self, issue, dtype):
        if dtype == "SLA":
            return self.trimmedSLAIssue(issue)
        elif dtype == "FTS":
            return self.trimmedFTSIssue(issue)
        elif dtype == "REV":
            return self.trimmedREVDoc(issue)
        else:
            return self.trimmedIssue(issue)

    def trimmedSLAIssue(self, issue):
        """Trim an SLA issue to just it's id and the number of hours and minutes
        until it expires."""
        now = datetime.utcnow()
        started = issue.doc["sla"]["startAt"].replace(tzinfo=None)
        expires = issue.doc["sla"]["expireAt"].replace(tzinfo=None)
        if started != expires:
            percent_expired = (now - started).total_seconds() \
                / (expires - started).total_seconds() * 100
        else:
            percent_expired = 0
        percent_expired = min(percent_expired, 99.999)
        return {"id": issue.doc["jira"]["key"],
                "priority": issue.priority,
                "assignee": issue.assigneeDisplayName,
                "total_seconds": (expires-now).total_seconds(),
                "percentExpired": percent_expired,
                "desc": issue.doc['jira']['fields']['summary']}


    def trimmedFTSIssue(self, issue):
        """Trim an FTS issue to just it's id and the number of hours and minutes
        since someone with a mongodb email commented publicly on it."""
        now = datetime.utcnow()
        allComments = issue.doc['jira']['fields']['comment']['comments']
        lastComment = issue.lastXGenPublicComment
        if lastComment is None:
            lastUpdate = issue.updated.replace(tzinfo=None)
        else:
            # Need when the issue was updated, not just created, so get all the
            # comment info
            lastUpdate = allComments[lastComment['cidx']]["updated"].replace(tzinfo=None)
        mins = (now - lastUpdate).seconds / 60
        days = (now - lastUpdate).days
        return {"id": issue.doc["jira"]["key"],
                "priority": issue.priority,
                "assignee": issue.assigneeDisplayName,
                "days": days,
                "hours": mins / 60,
                "minutes": mins % 60,
                "desc": issue.doc['jira']['fields']['summary']}

    def trimmedREVDoc(self, doc):
        """Trim a REV issue to just it's id and the number of hours and minutes
        since it was created. Note here the doc does not have all the JIRA fields,
        but lives in a separate reviews collection"""
        
        """This is sketchy here. I think I just throw away 
        the tzinfo extension. Have to check this functionality later"""
        now = datetime.utcnow()

        lastUpdate = doc["requested_at"]
        lastUpdate = lastUpdate.replace(tzinfo=None)

        mins = (now - lastUpdate).seconds / 60
        days = (now - lastUpdate).days
        eyes_on = doc["reviewers"]
        if 'lookers' in doc:
            eyes_on = doc['lookers'] + eyes_on
        if 'lgtms' in doc:
            lgtms = doc["lgtms"]
        else:
            lgtms = "None"
        return {"id": doc["key"],
                "days": days,
                "hours": mins / 60,
                "minutes": mins % 60,
                "requestedby": doc["requested_by"],
                "reviewers": eyes_on,
                "lgtms": lgtms}

    def trimmedIssue(self, issue):
        """Trim the general issue to a base set of fields TO BE DETERMINED."""
        now = datetime.utcnow()
        allComments = issue.doc['jira']['fields']['comment']['comments']
        lastComment = issue.lastXGenPublicComment
        if lastComment is None:
            lastUpdate = issue.updated.replace(tzinfo=None)
        elif lastComment['cidx'] == len(allComments) - 1:  # It's the last comment
            # Need when the issue was updated, not just created, so get all the
            # comment info
            lastUpdate = allComments[lastComment['cidx']]["updated"].replace(tzinfo=None)
        else:
            # There has been at least one comment since the public xgen
            # comment, so if there are any customer comments, base timing off the
            # first one.
            lastUpdate = allComments[lastComment['cidx']]["updated"].replace(tzinfo=None)
            i = lastComment['cidx'] + 1
            while i < len(allComments):
                if not isMongoDBEmail(allComments[i]['author']['emailAddress']):
                    # It's a customer
                    lastUpdate = allComments[i]["updated"].replace(tzinfo=None)
                    break
                i += 1
        mins = (now - lastUpdate).seconds / 60
        days = (now - lastUpdate).days
        return {"id": issue.doc["jira"]["key"],
                "priority": issue.priority,
                "assignee": issue.assigneeDisplayName,
                "days": days,
                "hours": mins / 60,
                "minutes": mins % 60,
                "desc": issue.doc['jira']['fields']['summary']}

    # ---------------------------------------------------------------------------
    # OTHER HELPERS
    # ---------------------------------------------------------------------------

    def sortData(self, dataWell, dataName):
        """ Takes in a dataWell and its type (such as SLA or FTS) and sorts it
        according to its data type. Should sorting be moved to Javascript?? """

        def ascendingTimeOrder(t1, t2):
            """A custom comparator to order based on the difference in times in
            seconds. """
            return cmp(t1['total_seconds'], t2['total_seconds'])

        def descendingTimeOrder(t1, t2):
            """A custom comparator to order based on the hour / minute properties
            of the issues. Puts largest times first."""
            return -cmp((t1['days'], t1['hours'], t1['minutes']),
                        (t2['days'], t2['hours'], t2['minutes']))

        def idOrder(t1, t2):
            return -cmp(t1['id'], t2['id'])

        sorters = {
            "SLA": ascendingTimeOrder,
            "FTS": descendingTimeOrder,
            "REV": descendingTimeOrder,
            "UNA": descendingTimeOrder, 
            "ACTS": descendingTimeOrder,
            "WAIT": descendingTimeOrder,
            "USERASSIGNED": descendingTimeOrder,
            "USERREVIEW": idOrder,  # Only cause idk how to sort these yet
            "USERREVIEWER": idOrder, # Only cause idk how to sort these yet
            "UNAS": descendingTimeOrder
        }

        sorter = {dataName:sorters[dataName]}
        for category in sorter:
            dataWell.sort(sorter[category])

    def start(self):
        """ Gentlemen, start your engines. """
        self.logger.info(os.getcwd())        

        self.logger.debug("start()")
        self.logger.info("tk is at REST")

        b = bottle.Bottle(autojson=False)
        bottle.TEMPLATE_PATH.insert(0, '%s/views' % self.args['root_webdir'])

        self.logger.info(self.args['root_webdir'])

        def tokenize(func):
            """ A decorator for bottle-route callback functions to pass
            auth_user cookies """
            def wrapped(*args, **kwargs):
                kwargs['token'] = bottle.request.cookies.get("auth_user", None)

                if kwargs['token'] is None:
                    return bson.json_util.dumps({'status':'error', 'message':'Login to Corp'})

                # if kwargs['token'] is None:
                #     kwargs['token'] = "jacob.ribnik"

                # unescape escaped html characters!!
                # just @ for now as there are plenty of user@10gen.com's
                if kwargs['token'] is not None:
                    kwargs['token'] = kwargs['token'].replace('%40', '@')
                return func(*args, **kwargs)
            return wrapped

        """ Not sure why this is necessary. Leaving for further investigation """
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

            self.logger.info(result)
            return bson.json_util.dumps(result)

        # ---------------------------------------------------------------------
        # Static Files
        # ---------------------------------------------------------------------

        @b.route('/js/<filename:re:.*\.js>')
        def send_js(filename):
            return bottle.static_file(filename, 
                root="%s/js" % self.args['root_webdir'], 
                mimetype="text/javascript")


        @b.route('/css/<filename:re:.*\.css>')
        def send_css(filename):
            return bottle.static_file(filename, 
                root='%s/css' % self.args['root_webdir'], 
                mimetype="text/css")


        @b.route('/fonts/<filename>')
        def send_fonts(filename):
            return bottle.static_file(filename, 
                root='%s/fonts' % self.args['root_webdir'])

        @b.route('/img/<filename:re:.*\.png>')
        def send_image(filename):
            return bottle.static_file(filename, 
                root='%s/img' % self.args['root_webdir'])

        @b.route('/')
        def index():
            return bottle.redirect('/dash')

        @b.route('/dash')
        # @tokenize
        def dash(**kwargs):
            return bottle.template('dash')

        @b.get('/login')
        def login():
            token = bottle.request.get_cookie("auth_user")

            # reimplement this when ported
            if token is None:
                return bson.json_util.dumps({'status':'error', 'message':'Login to Corp'})

            # if token is None:
            #     token = "jacob.ribnik"

            # unescape escaped html characters!!
            # just @ for now as there are plenty of user@10gen.com's
            token = token.replace('%40', '@')
            res = self.sc.getUserInfo(token=token)
            if res['status'] == 'success':
                self.logger.info(res)
                user = res['payload']
                cookies = [(prop, user[prop]) for prop in user]
            else:
                cookies = None
            # self.logger.info(pprint(res))
            # return response(res, cookies=cookies)
            return bson.json_util.dumps(user)

        """ This guy here is really the workhorse of the dashboard.
        All views are updated with ajax calls through this route. """
        @b.route('/ajax/<view>')
        @tokenize
        def ajax_response(view, **kwargs):
            try:
                data = self.getData(view.upper(), **kwargs)
            except Exception as err:
                logger.exception("Something went wrong in getData")
                return bson.json_util.dumps({
                    'status':"error", 
                    'message':"Internal error: " + str(err.message)
                })

            return bson.json_util.dumps(data)

        b.run(host=self.args['server_host'], port=self.args['server_port'])



if __name__ == "__main__":
    desc = "TK-421, why aren't you at your post?"

    if os.path.isfile("tk421.log"):
        os.remove("tk421.log")

    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument("--server-host", metavar="HOST",
                               default="localhost",
                               help="specify the tk host "
                                    "(default=localhost)")
    parser.add_config_argument("--server-port", metavar="PORT", type=int,
                               default=8070,
                               help="specify the tk port (default=8080)")
    parser.add_config_argument("--stapi-host", metavar="HOST",
                               default="localhost",
                               help="specify the karakuri host "
                                    "(default=localhost)")
    parser.add_config_argument("--stapi-port", metavar="PORT", type=int,
                               default=8080,
                               help="specify the karakuri port "
                                    "(default=8080)")
    # parser.add_config_argument("--sfdc-password", metavar="SFDCPASSWORD",
    #                            help="specify a SFDC password")
    # parser.add_config_argument("--sfdc-username", metavar="SFDCUSERNAME",
    #                            help="specify a SFDC username")
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                               "(default=mongodb://localhost:27017)")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/euphonia.pid",
                               help="specify a PID file "
                                    "(default=/tmp/euphonia.pid)")
    parser.add_config_argument("--root-webdir", metavar="DIRECTORY",
                               default="%s" % os.getcwd(),
                               help="specify the root web directory")
    # parser.add_config_argument("--token", metavar="TOKEN",
    #                            help="specify a user token to persist")
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
        tk = tk421(args)

        # Initialize SFDC++
        # try:
        #     sfdcpp = sfdcpp(args, e.mongo)
        #     sfdcpp.setLive(True)
        #     e.setSfdc(sfdcpp)
        # except Exception as exc:
        #     e.logger.exception("Could not load SFDC++")
        #     e.logger.exception(exc)

        tk.start()
        sys.exit(0)

    # Require a log file and preserve it while daemonized
    if args.log is None:
        print("Please specify a log file")
        sys.exit(1)

    # Lock it up. You better lock it up. Lock it up!
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

    # This is daemon territory - Not enough mana.
    context = daemon.DaemonContext(pidfile=pidfile,
                                   stderr=fh.stream, stdout=fh.stream)
    context.files_preserve = [fh.stream]
    # TODO implment signal_map // whats a signal map?

# -----------------------------------------------------------------------------
# LAUNCHING SERVER AS A DAEMON - My god... what have we done?
# -----------------------------------------------------------------------------

    print('Starting...')

    with context:
        tk = tk421(args)

        # Initialize SFDC++
        # try:
        #     sfdcpp = sfdcpp(args, e.mongo)
        #     sfdcpp.setLive(args.live)
        #     e.setSfdc(sfdcpp)
        # except Exception as exc:
        #     e.logger.exception("Could not load SFDC++")
        #     e.logger.exception(exc)

        tk.start()
sys.exit(0)
