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
from wsgiproxy.app import WSGIProxyApp


# Timedelta has a new method in 2.7 that has to be hacked for 2.6
import ctypes as c
_get_dict = c.pythonapi._PyObject_GetDictPtr
_get_dict.restype = c.POINTER(c.py_object)
_get_dict.argtypes = [c.py_object]

try:
    timedelta.total_seconds
except AttributeError:
    def total_seconds(td):
        return float((td.microseconds +
                      (td.seconds + td.days * 24 * 3600) * 10**6)) / 10**6
    d = _get_dict(timedelta)[0]
    d['total_seconds'] = total_seconds

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
        #REMOVE
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

    def getIssues(self, data):
        """The workhorse of refreshing the page. Given data, containing the
        currently displayed issues and the time they were last updated, update it
        to contain the issues that should appear on the dashboard.
        (SLA: Service Level Agreement, we are contractually obligated to respond in
             a certain amount of time to these issues, but haven't yet.
         FTS: Full Time Support, issues that need 24 hr monitoring. They are tagged
             as such in jira.
         REV: Reviews, issues needing review from peers. Stored in a separate
             collection in mongo.
         UNA: Unnassigned, issues with no assignee with the last comment made by a
             non-mongodb employee)"""
        start = datetime.utcnow()  # Time this and log how long refreshing took.
        # try:
        #     cur = self.getRelevantIssues(db, data)
        # except pymongo.errors.PyMongoError as e:
        #     return {"error": "Error querying the Mongo database: " +
        #             e.message}

        # slas = self.sc.getActiveSLAs()

        """ What the hell is this line doing to break everything ?????? """
        fts = self.sc.getActiveFTSs()

        unas = self.sc.getActiveUNAs()

        acts = self.sc.getActiveIssues()

        # dt = int((time.time() - stime)*1000)
        # logfile.write("Time to after getRelevantIssues() run: ")
        # print >> logfile, dt

        count = 0
        dbd_data = {
            # TODO: make sets of these to make the lookups below faster
            "SLA": data.get("SLA", []),
            "FTS": data.get("FTS", []),
            "REV": [],  # Just refresh these every time
            "UNA": data.get("UNA", []),
            "ACTS": data.get("ACTS", [])
            # "active": data.get("active", {}),
            # "waiting": data.get("waiting", {})
        }

        try:
            revIssues = self.getREVIssues()
        except pymongo.errors.PyMongoError as e:
            return {"error": "Error querying the Mongo database: " +
                    e.message}

        # revIssues = []

        updated_data = {
            "SLA": [],
            "FTS": [],
            "REV": revIssues,
            "UNA": [],
            "ACTS": []
        }

        # self.logger.info(cur)
        # self.logger.info("cur\n")

        # for i in slas:
        #     issue = SupportIssue().fromDoc(i)

        #     self.removeCompressedIssueIfPresent(issue, dbd_data["SLA"])
        #     if self.isSLA(issue):
        #         updated_data["SLA"].append(self.trimmedSLAIssue(issue))

        for i in fts:
            issue = SupportIssue().fromDoc(i)

            self.removeCompressedIssueIfPresent(issue, dbd_data["FTS"])
            if self.isFTS(issue):
                updated_data["FTS"].append(self.trimmedFTSIssue(issue))

        for i in unas:
            issue = SupportIssue().fromDoc(i)

            self.removeCompressedIssueIfPresent(issue, dbd_data["UNA"])
            if self.isUNA(issue):
                updated_data["UNA"].append(self.trimmedUNAIssue(issue))

        for i in acts:
            issue = SupportIssue().fromDoc(i)

            self.removeCompressedIssueIfPresent(issue, dbd_data["ACTS"])
            if issue.isActive():# and not self.isSLA(issue) and not self.isFTS(issue) and not self.isUNA(issue):
                updated_data["ACTS"].append(self.trimmedACTSIssue(issue)) # self.trimmedACTSIssue(issue)

        self.mergeAndSortIssues(dbd_data, updated_data)

        duration = datetime.utcnow() - start
        logger.info("getIssues took {0}, count: {1}".format(duration, count))

        return dbd_data

    def getSLAs(self, data):
        start = datetime.utcnow()  # Time this and log how long refreshing took.

        slas = self.sc.getActiveSLAs()

        dbd_data = {
            # TODO: make sets of these to make the lookups below faster
            "SLA": data.get("SLA", [])
        }
        # revIssues = []

        updated_data = {
            "SLA": []
        }

        for i in slas:
            issue = SupportIssue().fromDoc(i)

            self.removeCompressedIssueIfPresent(issue, dbd_data["SLA"])
            if self.isSLA(issue):
                updated_data["SLA"].append(self.trimmedSLAIssue(issue))

        self.mergeAndSortIssuesSLAs(dbd_data, updated_data)

        return dbd_data

    def getFTSs(self, data):
        start = datetime.utcnow()  # Time this and log how long refreshing took.

        fts = self.sc.getActiveFTSs()

        dbd_data = {
            # TODO: make sets of these to make the lookups below faster
            "FTS": data.get("FTS", [])
        }
        # revIssues = []

        updated_data = {
            "FTS": []
        }

        for i in fts:
            issue = SupportIssue().fromDoc(i)

            self.removeCompressedIssueIfPresent(issue, dbd_data["FTS"])
            if self.isFTS(issue):
                updated_data["FTS"].append(self.trimmedFTSIssue(issue))

        self.mergeAndSortIssuesFTSs(dbd_data, updated_data)

        return dbd_data

    def getUNAs(self, data):
        start = datetime.utcnow()  # Time this and log how long refreshing took.

        unas = self.sc.getActiveUNAs()

        dbd_data = {
            # TODO: make sets of these to make the lookups below faster
            "UNA": data.get("UNA", [])
        }
        # revIssues = []

        updated_data = {
            "UNA": []
        }

        for i in unas:
            issue = SupportIssue().fromDoc(i)

            self.removeCompressedIssueIfPresent(issue, dbd_data["UNA"])
            if self.isUNA(issue):
                updated_data["UNA"].append(self.trimmedUNAIssue(issue))

        self.mergeAndSortIssuesUNAs(dbd_data, updated_data)

        return dbd_data

    def getREVs(self, data):
        start = datetime.utcnow()  # Time this and log how long refreshing took.

        dbd_data = {
            # TODO: make sets of these to make the lookups below faster
            "REV": data.get("FTS", [])
        }
        # revIssues = []

        updated_data = {
            "REV": self.getREVIssues()
        }

        self.mergeAndSortIssuesREVs(dbd_data, updated_data)

        return dbd_data

    def getACTS(self, data):
        start = datetime.utcnow()  # Time this and log how long refreshing took.

        acts = self.sc.getActiveIssues()

        dbd_data = {
            # TODO: make sets of these to make the lookups below faster
            "ACTS": data.get("ACTS", [])
        }
        # revIssues = []

        updated_data = {
            "ACTS": []
        }

        for i in acts:
            issue = SupportIssue().fromDoc(i)

            self.removeCompressedIssueIfPresent(issue, dbd_data["ACTS"])
            if issue.isActive():# and not self.isSLA(issue) and not self.isFTS(issue) and not self.isUNA(issue):
                updated_data["ACTS"].append(self.trimmedACTSIssue(issue)) # self.trimmedACTSIssue(issue)

        self.mergeAndSortIssuesACTS(dbd_data, updated_data)

        return dbd_data

    def getRelevantIssues(self, db, data):
        """If updating dashboard, query for issues that have been updated since the
        last load. Otherwise query for all relevant issues. data will be empty if
        this is the first query."""
        last_updated = data.get('updated', None)
        # last_updated = "2015-07-01T16:54:45.908Z"
        if last_updated is not None:
            cur = self.sc.getUpdatedIssues(last_updated)
        else:
            cur = self.sc.getActiveIssues()

        ## ---- This was the old call. This is replaced with a call to stAPI ----- #
        # cur = db.issues.find(query, proj)
        # cur.batch_size(100000)
        ## ----------------------------------------------------------------------- #
        
        return cur


    # -----------------------------------------------------------------------------
    # FILTERS (decide which issues should be displayed on the dashboard)
    # -----------------------------------------------------------------------------


    def getREVIssues(self):
        # """No fancy logic necessary here, just post all issues needing review."""
        reviews = self.sc.getActiveReviews()
        # self.logger.info(reviews)
        # reviews = doc['data']['reviews']
        revs_trim = []
        for review in reviews:
            revs_trim.append(self.trimmedREVDoc(review))

        return revs_trim

        # ----------- Old calls. Replaced by call to stAPI ------------------------------- #
        # return map(self.trimmedREVDoc, self.sc.getActiveReviews())
        # return map(self.trimmedREVDoc,
        #            db.reviews.find({"done": False})) # , "lgtms": {"$exists": False}
        # -------------------------------------------------------------------------------- #


    def isSLA(self, issue):
        """Return true if the issue should be displayed in the SLA row of the
        dashboard."""
        return (issue.isActive() and
                issue.hasSLA() and
                'expireAt' in issue.doc['sla'] and
                issue.doc['sla']['expireAt'] is not None and
                ((not issue.isProactive() and issue.firstXGenPublicComment is None)
                    or (issue.isProactive() and
                        issue.firstXGenPublicCommentAfterCustomerComment is None)))


    def isFTS(self, issue):
        """Return true if the issue should be displayed in the FTS row of the
        dashboard."""
        return (issue.isActive() and
                issue.isFTS())


    def isUNA(self, issue):
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

    # -----------------------------------------------------------------------------
    # TRIMMERS (trim issue with extra info into just what's needed to display it)
    # -----------------------------------------------------------------------------

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

    def trimmedUNAIssue(self, issue):
        """Trim a UNA issue to just it's id and the number of hours and minutes
        since the last public xgen comment (the last time we've paid attention to
        it)."""
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

    def trimmedACTSIssue(self, issue):
        """Trim the remaining active issues to a base set of fields TO BE DETERMINED."""
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


    # -----------------------------------------------------------------------------
    # OTHER HELPERS
    # -----------------------------------------------------------------------------


    def mergeAndSortIssues(self, dbd_issues, updated_issues):
        """Add the issues that were updated to the lists of issues on the
        dashboard and (re)sort them by priority. The priority will be the time, but
        which order we want them in depends on the type of issue."""

        def ascendingTimeOrder(t1, t2):
            """A custom comparator to order based on the difference in times in
            seconds. """
            return cmp(t1['total_seconds'], t2['total_seconds'])

        def descendingTimeOrder(t1, t2):
            """A custom comparator to order based on the hour and minute properties
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
            "ACTS": descendingTimeOrder
        }

        self.logger.info(dbd_issues)
        self.logger.info("dbd issues in NON slas")

        for category in sorters:
            if category is not "ACTS":
                dbd_issues[category].extend(updated_issues[category])
                dbd_issues[category].sort(sorters[category])
            elif category is "ACTS":
                dbd_issues[category].extend(updated_issues[category])

    def mergeAndSortIssuesSLAs(self, dbd_issues, updated_issues):

        def ascendingTimeOrder(t1, t2):
            return cmp(t1['total_seconds'], t2['total_seconds'])

        sorters = {
            "SLA": ascendingTimeOrder
        }

        for category in sorters:
            dbd_issues[category].extend(updated_issues[category])
            dbd_issues[category].sort(sorters[category])

    def mergeAndSortIssuesFTSs(self, dbd_issues, updated_issues):

        def descendingTimeOrder(t1, t2):
            return -cmp((t1['days'], t1['hours'], t1['minutes']),
                        (t2['days'], t2['hours'], t2['minutes']))

        sorters = {
            "FTS": descendingTimeOrder
        }
        for category in sorters:
            dbd_issues[category].extend(updated_issues[category])
            dbd_issues[category].sort(sorters[category])

    def mergeAndSortIssuesUNAs(self, dbd_issues, updated_issues):

        def descendingTimeOrder(t1, t2):
            return -cmp((t1['days'], t1['hours'], t1['minutes']),
                        (t2['days'], t2['hours'], t2['minutes']))

        sorters = {
            "UNA": descendingTimeOrder
        }
        for category in sorters:
            dbd_issues[category].extend(updated_issues[category])
            dbd_issues[category].sort(sorters[category])

    def mergeAndSortIssuesACTS(self, dbd_issues, updated_issues):

        def descendingTimeOrder(t1, t2):
            return -cmp((t1['days'], t1['hours'], t1['minutes']),
                        (t2['days'], t2['hours'], t2['minutes']))

        sorters = {
            "ACTS": descendingTimeOrder
        }
        for category in sorters:
            dbd_issues[category].extend(updated_issues[category])

    def mergeAndSortIssuesREVs(self, dbd_issues, updated_issues):

        def descendingTimeOrder(t1, t2):
            return -cmp((t1['days'], t1['hours'], t1['minutes']),
                        (t2['days'], t2['hours'], t2['minutes']))

        sorters = {
            "REV": descendingTimeOrder
        }
        for category in sorters:
            dbd_issues[category].extend(updated_issues[category])
            dbd_issues[category].sort(sorters[category])

    def removeCompressedIssueIfPresent(self, issue, compressed_issues):
        """compressed_issues is a list of issues, but stripped down to just the
        information relevant to display them. Search through that list and remove
        the issue that has the same key as the one given, if one exists."""
        for i in compressed_issues:
            if i['id'] == issue.key:
                compressed_issues.remove(i)
                return

    def start(self):
        """ Start the RESTful interface """
        self.logger.info(os.getcwd())        

        self.logger.debug("start()")
        self.logger.info("tk is at REST")

        b = bottle.Bottle(autojson=False)
        bottle.TEMPLATE_PATH.insert(0, '%s/views' % self.args['root_webdir'])

        self.logger.info(self.args['root_webdir'])

        # def tokenize(func):
        #     """ A decorator for bottle-route callback functions to pass
        #     auth_user cookies """
        #     def wrapped(*args, **kwargs):
        #         # NOTE this is a corp cookie!
        #         kwargs['token'] = bottle.request.get_cookie("auth_user", '')
        #         # unescape escaped html characters!!
        #         # just @ for now as there are plenty of user@10gen.com's
        #         if kwargs['token'] is not None:
        #             kwargs['token'] = kwargs['token'].replace('%40', '@')
        #         return func(*args, **kwargs)
        #     return wrapped

        # -----------------------------------------------------------------------------
        # Static Files
        # -----------------------------------------------------------------------------

        @b.route('/js/<filename:re:.*\.js>')
        def send_js(filename):
            return bottle.static_file(filename, 
                root="%s/js" % self.args['root_webdir'], mimetype="text/javascript")


        @b.route('/css/<filename:re:.*\.css>')
        def send_css(filename):
            return bottle.static_file(filename, 
                root='%s/css' % self.args['root_webdir'], mimetype="text/css")


        @b.route('/fonts/<filename>')
        def send_fonts(filename):
            return bottle.static_file(filename, root='%s/fonts' % self.args['root_webdir'])

        @b.route('/img/<filename:re:.*\.png>')
        def send_image(filename):
            return bottle.static_file(filename, root='%s/img' % self.args['root_webdir'])

        @b.route('/dash')
        # @tokenize
        def index():
            # return bottle.template('dash_home')
            return bottle.template('test')

        @b.route('/ajax/sla')
        def ajax_response():
            try:
                if (bottle.request.json):# and 'totals' in bottle.request.json):
                    slas = self.getSLAs(bottle.request.json)

                else:
                    slas = self.getSLAs({})
            except Exception as err:
                logger.exception("Something went wrong in getIssues.")
                return bson.json_util.dumps({"error": "Internal error: " + err.message})

            return bson.json_util.dumps(slas)

        @b.route('/ajax/fts')
        def ajax_response():
            try:
                if (bottle.request.json):# and 'totals' in bottle.request.json):
                    fts = self.getFTSs(bottle.request.json)

                else:
                    fts = self.getFTSs({})
            except Exception as err:
                logger.exception("Something went wrong in getIssues.")
                return bson.json_util.dumps({"error": "Internal error: " + err.message})

            return bson.json_util.dumps(fts)

        @b.route('/ajax/una')
        def ajax_response():
            try:
                if (bottle.request.json):# and 'totals' in bottle.request.json):
                    una = self.getUNAs(bottle.request.json)

                else:
                    una = self.getUNAs({})
            except Exception as err:
                logger.exception("Something went wrong in getIssues.")
                return bson.json_util.dumps({"error": "Internal error: " + err.message})

            return bson.json_util.dumps(una)

        @b.route('/ajax/acts')
        def ajax_response():
            try:
                if (bottle.request.json):# and 'totals' in bottle.request.json):
                    acts = self.getACTS(bottle.request.json)

                else:
                    acts = self.getACTS({})
            except Exception as err:
                logger.exception("Something went wrong in getIssues.")
                return bson.json_util.dumps({"error": "Internal error: " + err.message})

            return bson.json_util.dumps(acts)

        @b.route('/ajax/rev')
        def ajax_response():
            try:
                if (bottle.request.json):# and 'totals' in bottle.request.json):
                    rev = self.getREVs(bottle.request.json)

                else:
                    rev = self.getREVs({})
            except Exception as err:
                logger.exception("Something went wrong in getIssues.")
                return bson.json_util.dumps({"error": "Internal error: " + err.message})

            return bson.json_util.dumps(rev)

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

# -----------------------------------------------------------------------------
# LAUNCHING SERVER AS A DAEMON
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
