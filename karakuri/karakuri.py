#!/usr/bin/env python


import argumentparserpp
import bottle
import bson
import bson.json_util
import copy
import daemon
import gzip
import logging
import os
import pidlockfile
import pymongo
import re
import signal
import string
import StringIO
import sys
import isodate

from datetime import datetime, timedelta
from jirapp import jirapp
from sfdcpp import sfdcpp
from supportissue import SupportIssue
from ses_handler import SESHandler


# TODO move to python-lib
def getSubdocs(doc, projection):
    # get the subdocuments based on the projection
    # similar to how projection works in the find command
    # NOTE plural because we expand arrays
    res = []
    subdoc = doc
    subdocTree = projection.split(".")
    # iterate through the subdocuments
    for i in range(len(subdocTree)):
        key = subdocTree[i]
        # if subdoc is an array, we must loop over it
        # for the rest of the projection
        if isinstance(subdoc, list):
            for item in subdoc:
                res.extend(getSubdocs(item, '.'.join(subdocTree[i:])))
            return res
        elif subdoc is None:
            pass
        else:
            if key in subdoc:
                subdoc = subdoc[key]
            else:
                subdoc = None
                break
    res.append(subdoc)
    return res


class karakuri:
    """ An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D """
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.logger = logging.getLogger("logger")

        self.jira = None
        self.sfdc = None
        # The issue tracking system
        self.issuer = None

        # Are we hot!?
        self.live = self.args['live']

        # Throttle limits are infinite by default
        if self.args['global_limit'] is None:
            self.global_limit = sys.maxint
        else:
            self.global_limit = self.args['global_limit']

        if self.args['user_limit'] is None:
            self.user_limit = sys.maxint
        else:
            self.user_limit = self.args['user_limit']

        if self.args['company_limit'] is None:
            self.company_limit = sys.maxint
        else:
            self.company_limit = self.args['company_limit']

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.coll_issues = self.mongo.support.issues
        self.coll_companies = self.mongo.support.companies
        self.coll_workflows = self.mongo.karakuri.workflows
        self.coll_log = self.mongo.karakuri.log
        self.coll_queue = self.mongo.karakuri.queue
        self.coll_users = self.mongo.karakuri.users

        # Global, user and company throttles
        self.throttle = {}

    def _amiThrottling(self, **kwargs):
        """ Have we reached a processing limit? Return bool """
        self.logger.debug("_amiThrottling()")
        self.throttleRefresh(**kwargs)
        if kwargs['approvedBy'] not in self.throttle['users']:
            self.throttle['users'][kwargs['approvedBy']] = 0
        if kwargs['company'] not in self.throttle['companies']:
            self.throttle['companies'][kwargs['company']] = 0
        return self.throttle['global'] >= self.global_limit or\
            self.throttle['users'][kwargs['approvedBy']] >= self.user_limit or\
            self.throttle['companies'][kwargs['company']] >= self.company_limit

    def _hasTaskPrivileges(self, tid, mode="r", **kwargs):
        """ Does requesting user have sufficient privileges? """
        if 'admin' in kwargs['userDoc'].get('groups', []):
            return True
        res = self.getTask(tid)
        if not res['ok']:
            # TODO this should really throw an exception
            return False
        task = res['payload']
        workflowName = task['workflow']
        return self._hasWorkflowPrivileges(workflowName, mode, **kwargs)

    def _hasWorkflowPrivileges(self, workflowName, mode="r", **kwargs):
        """ Does requesting user have sufficient privileges? """
        if 'admin' in kwargs['userDoc'].get('groups', []):
            return True

        res = self.getWorkflow(workflowName)
        if not res['ok']:
            # TODO this should really throw an exception
            return False
        wf = res['payload']

        # read-write-execute
        if 'owner' in wf and wf['owner'] == kwargs['userDoc']['user']:
            return True
        if mode == "r" or mode == "e":
            if 'public' in wf and wf['public'] is True:
                return True
            # Group-level check
            for group in kwargs['userDoc'].get('groups', []):
                if group in wf.get('groups', []):
                    return True
        return False

    def approveTask(self, tid, **kwargs):
        """ Approve the task for processing """
        self.logger.debug("approveTask(%s)", tid)
        if not self._hasTaskPrivileges(tid, 'e', **kwargs):
            return {'ok': False, 'payload': 'Insufficient privileges'}
        updoc = {"$set": {'approved': True,
                          'approvedBy': kwargs['userDoc']['user']}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'approve', res['ok'], **kwargs)
        return res

    def _buildQuery(self, query, task=None, **kwargs):
        self.logger.debug("_buildQuery(%s,%s)", query, task)
        # Replace template variables with real values. A template variable is
        # identified as capital letters between double square brackets
        pattern = re.compile('\[\[([0-9A-Z_]+)\]\]')
        # Use a set to remove repeats
        matches = set(pattern.findall(query))
        if task is None:
            override = {}
        else:
            override = {'CURRENT_USER': task['createdBy']}
        for match in matches:
            res = self._getTemplateQueryValue(match, override, **kwargs)
            if not res['ok']:
                return res
            val = res['payload']
            query = query.replace('[[%s]]' % match, val)
        return self.loadJson(query)

    def buildValidateQuery(self, workflowNameORworkflow, _id=None, task=None,
                           **kwargs):
        """ Return a MongoDB query that accounts for the workflow prerequisites
        """
        # TODO choose either workflowName or workflow
        self.logger.debug("buildValidateQuery(%s,%s,%s)",
                          workflowNameORworkflow, _id, task)
        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow, **kwargs)
            if not res['ok']:
                return res
            workflow = res['payload']
        res = self._buildQuery(workflow['query_string'], task, **kwargs)
        if not res['ok']:
            return res
        match = res['payload']

        if _id is not None:
            # the specified _id must return in the query!
            res = self.getObjectId(_id)
            if not res['ok']:
                return res
            _id = res['payload']
            match['_id'] = _id

        # in UTC please!
        now = datetime.utcnow()

        if 'prereqs' in workflow and len(workflow['prereqs']) != 0:
            # require that each prerequisite has been met
            prereqs = workflow['prereqs']

            if "$and" not in match:
                match["$and"] = []

            for prereq in prereqs:
                # time elapsed since prereq logged
                time_elapsed = timedelta(seconds=prereq['time_elapsed'])
                start = now - time_elapsed
                # TODO allow for prereqs outside of active_states, i.e. in
                # workflows_performed
                match['$and'].append({'karakuri.active_states':
                                     {"$elemMatch":
                                      {'name': prereq['name'],
                                       'updated': {"$lte": start}}}})
        return {'ok': True, 'payload': match}

    def createIssue(self, fields, **kwargs):
        """ Create a new issue """
        self.logger.debug("createIssue(%s)", fields)
        callbacks = None
        if 'karakuri' in fields and fields['karakuri'] is not None:
            # These arguments are for us, not the ticket
            callbacks = copy.deepcopy(fields['karakuri'])
            del fields['karakuri']
        fields = SupportIssue(fields).getJIRAFields()
        res = self.issuer.createIssue(fields)
        if not res['ok']:
            return res
        key = res['payload']
        self.logger.info("Created issue %s", key)
        # Execute callbacks if there are any
        if callbacks is not None:
            for cb in callbacks:
                # Add developer comment to newly created ticket if specified
                if 'addDeveloperComment' in cb and\
                        cb['addDeveloperComment'] is not None:
                    res1 = self.issuer.\
                        addDeveloperComment(key, cb['addDeveloperComment'])
                    if not res1['ok']:
                        # Not returning on failure because the caller expects
                        # an issue key if the issue was created. That's more
                        # important than the result of this addDeveloperComment
                        # action
                        self.logger.\
                            warning("Failed to add developer comment to %s",
                                    key)
        return res

    def createUser(self, user, **kwargs):
        """ Create a new user with appropriate defaults """
        self.logger.debug("createUser(%s)", user)

        match = {'user': user}
        updoc = {'groups': [],
                 'name': 'Dude',
                 'token_created_date': datetime.now(),
                 'token_expiry_date': datetime.max,
                 'workflows': ["MyOpenTickets"]}
        # third argument is upsert
        return self.find_and_modify_user(match, updoc, True)

    def createWorkflow(self, fields, **kwargs):
        """ Create a new workflow """
        self.logger.debug("createWorkflow(%s)", fields)

        # only admins can set auto-approve
        if 'auto_approve' in fields and fields['auto_approve'] is True and\
                'admin' not in kwargs['userDoc']['groups']:
            return {'ok': False,
                    'payload': "only admins can set auto-approve"}

        res = self.validateWorkflow(fields, **kwargs)
        if not res['ok']:
            return res

        # does a workflow with this name already exist?
        res = self.getWorkflow(fields['name'], **kwargs)
        if res['ok']:
            return {'ok': False, 'payload': "workflow '%s' already exists"
                    % fields['name']}

        # the submitter is the owner
        fields['owner'] = kwargs['userDoc']['user']

        try:
            self.coll_workflows.insert(fields)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': fields}

    def deleteWorkflow(self, name, **kwargs):
        """ Delete the workflow """
        try:
            self.coll_workflows.remove({'name': name})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': None}

    def disapproveTask(self, tid, **kwargs):
        """ Disapprove the task for processing """
        self.logger.debug("disapproveTask(%s)", tid)
        if not self._hasTaskPrivileges(tid, 'e', **kwargs):
            return {'ok': False, 'payload': 'Insufficient privileges'}
        updoc = {"$set": {'approved': False}, "$unset": {'approvedBy': ""}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'disapprove', res['ok'], **kwargs)
        return res

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

    def find_and_modify_task(self, match, updoc):
        """ find_and_modify for karakuri.queue that automatically updates the
        't' timestamp """
        self.logger.debug("find_and_modify_task(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}
        return self.find_and_modify(self.coll_queue, match, updoc)

    def find_and_modify_user(self, match, updoc, upsert=False):
        """ find_and_modify for karakuri.users that automatically updates the
        't' timestamp """
        self.logger.debug("find_and_modify_user(%s,%s)", match, updoc)
        if upsert is True:
            updoc['user'] = match['user']
            updoc['t'] = datetime.utcnow()
        else:
            if "$set" in updoc:
                updoc["$set"]['t'] = datetime.utcnow()
            else:
                updoc["$set"] = {'t': datetime.utcnow()}
        return self.find_and_modify(self.coll_users, match, updoc,
                                    upsert=upsert)

    def find_and_modify_workflow(self, match, updoc):
        """ find_and_modify for karakuri.workflows that automatically updates
        the 't' timestamp """
        self.logger.debug("find_and_modify_workflow(%s,%s)", match, updoc)
        if "$set" in updoc:
            updoc["$set"]['t'] = datetime.utcnow()
        else:
            updoc["$set"] = {'t': datetime.utcnow()}
        return self.find_and_modify(self.coll_workflows, match, updoc)

    def find_one(self, collection, match):
        """ Wrapper for find_one that handles exceptions """
        self.logger.debug("find_one(%s,%s)", collection, match)
        try:
            doc = collection.find_one(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': doc}

    def findTasks(self, **kwargs):
        """ Find and queue new tasks """
        self.logger.debug("findTasks()")
        res = self.getListOfWorkflows(**kwargs)
        if not res['ok']:
            return res
        workflows = res['payload']

        tasks = []
        for workflow in workflows:
            res = self.findWorkflowTasks(workflow, **kwargs)
            if not res['ok']:
                return res
            tasks += res['payload']
        return {'ok': True, 'payload': tasks}

    def findWorkflowDocs(self, workflow, **kwargs):
        """ Return list of docs that satisfy the workflow """
        self.logger.debug("findWorkflowDocs(%s)", workflow)
        # If there is more than one query, then we are using joins
        # Preqreqs, time elapsed, etc. apply only to primary query though
        nQueries = 1
        while ("ns%s" % nQueries) in workflow:
            nQueries += 1

        if nQueries > 1:
            # array of join key value -> doc dicts
            results = []

            for i in range(0, nQueries):
                if i == 0:
                    res = self.buildValidateQuery(workflow, **kwargs)
                    if not res['ok']:
                        return res
                    match = res['payload']
                    ns = workflow['ns']
                    joinKey = workflow['join_key']
                else:
                    query_string = workflow['query_string%s' % i]
                    res = self._buildQuery(query_string, **kwargs)
                    if not res['ok']:
                        return res
                    match = res['payload']

                    # include join key values from previous query in this query
                    keys = results[i-1].keys()
                    joinKey = workflow['join_key%s' % i]

                    if "$and" in match:
                        match["$and"].append({joinKey: {"$in": keys}})
                    else:
                        if joinKey in match:
                            match["$and"] = [{joinKey: match[joinKey]},
                                             {joinKey: {"$in": keys}}]
                            del match[joinKey]
                        else:
                            match[joinKey] = {"$in": keys}
                    ns = workflow['ns%s' % i]

                # the doc collection
                (db, coll) = ns.split('.')

                try:
                    curs = self.mongo[db][coll].find(match)
                except pymongo.errors.PyMongoError as e:
                    self.logger.exception(e)
                    return {'ok': False, 'payload': e}

                # join key value -> doc dict
                result = {}
                for doc in curs:
                    joinKeyValues = getSubdocs(doc, joinKey)
                    if joinKeyValues is not None:
                        for joinKeyValue in joinKeyValues:
                            result[joinKeyValue] = doc
                    else:
                        # skip doc if it does not include join key
                        continue
                results.append(result)

            # final intersection of keys is the set of keys in the last result
            # since we've been propagating them through the queries
            keys = results[-1].keys()

            # merge results docs over keys for the final result with a unique
            # primary result _id
            res = {}
            for key in keys:
                for i in range(len(results)):
                    result = results[i]
                    if key in result:
                        if i == 0:
                            # do we already have this primary _id in the final
                            # result?
                            _id = result[key]['_id']
                            if _id not in res:
                                res[_id] = result[key]
                                res[_id]['joins'] = []
                        else:
                            res[_id]['joins'].append(result[key])
            return {'ok': True, 'payload': res.values()}
        else:
            res = self.buildValidateQuery(workflow, **kwargs)
            if not res['ok']:
                return res
            match = res['payload']

            # the doc collection
            ns = workflow['ns']
            (db, coll) = ns.split('.')

            try:
                curs = self.mongo[db][coll].find(match)
            except pymongo.errors.PyMongoError as e:
                self.logger.exception(e)
                return {'ok': False, 'payload': e}
            return {'ok': True, 'payload': [doc for doc in curs]}

    def findWorkflowTasksIssues(self, workflow, **kwargs):
        res = self.getListOfTasks({'workflow': workflow, 'active': True})
        if not res['ok']:
            return res
        tasks = res['payload']
        issues = []
        for task in tasks:
            issues.append(task['iid'])
        try:
            curs_issues = self.coll_issues.find({"_id": {"$in": issues}})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [issue for issue in curs_issues]}

    def findWorkflowTasksIssuesSummaries(self, workflow, **kwargs):
        res = self.getListOfTasks({'workflow': workflow, 'active': True},
                                  **kwargs)
        if not res['ok']:
            return res
        tasks = res['payload']
        issues = []
        projection = {'jira.fields.assignee': 1,
                      'jira.key': 1,
                      'jira.fields.status': 1,
                      'jira.fields.customfield_10030': 1,
                      'karakuri.workflows_performed': 1
                      }
        for task in tasks:
            issues.append(task['iid'])
        try:
            curs_issues = self.coll_issues.find({"_id": {"$in": issues}},
                                                projection)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [issue for issue in curs_issues]}

    def findWorkflowTasks(self, workflowNameORworkflow, **kwargs):
        """ Find docs that satisfy the workflow and queue new tasks """
        self.logger.debug("findWorkflowTasks(%s)", workflowNameORworkflow)
        if isinstance(workflowNameORworkflow, dict):
            workflow = workflowNameORworkflow
        else:
            res = self.getWorkflow(workflowNameORworkflow, **kwargs)
            if not res['ok']:
                return res
            workflow = res['payload']
        ns = workflow['ns']

        res = self.findWorkflowDocs(workflow, **kwargs)
        if not res['ok']:
            return res
        docs = res['payload']

        tasks = []
        for i in docs:
            issue = SupportIssue()
            if ns == 'support.issues':
                issue.fromDoc(i)
            elif ns == 'support.changelog':
                if i['src'] == 'jira':
                    res = self.getIssue(i['meta']['issueId'])
                    if not res['ok']:
                        return res
                    issue.fromDoc(res['payload'])
            else:
                # TODO throw exception
                pass

            # we only support JIRA at the moment
            # TODO logic for multiple issuers
            if not issue.hasJIRA():
                self.logger.warning("Skipping unsupported ticket type!")
                continue

            # check for karakuri sleepy time
            if not issue.isAwake():
                self.logger.info("Skipping %s as it is not awake" % issue.key)
                continue

            tid = bson.ObjectId()
            task = {'_id': tid,
                    'id': i['_id'],
                    'workflow': workflow['name'],
                    'company': issue.company,
                    'iid': i['_id'],
                    'done': False,
                    'key': issue.key,
                    'inProg': False,
                    'active': False,
                    'createdBy': kwargs['userDoc'].get('user'),
                    'ns': workflow['ns']}
            res = self.validateTask(task)
            if res['ok'] and res['payload']:
                res = self.queueTask(tid, workflow['ns'], i['_id'],
                                     workflow['name'], issue.id, issue.key,
                                     issue.company, **kwargs)
                self._log(tid, "queue", res['ok'], **kwargs)
                if not res['ok']:
                    return res
                if res['payload'] is not None:
                    tasks.append(res['payload'])
        return {'ok': True, 'payload': tasks}

    def forListOfTaskIds(self, action, tids, **kwargs):
        """ Perform the given action for the specified tasks """
        self.logger.debug("forListOfTaskIds(%s,%s)", action.__name__, tids)
        tasks = []
        messages = []
        for tid in tids:
            res = action(tid, **kwargs)
            if not res['ok']:
                self.logger.warning(res['payload'])
                messages.append(res['payload'])
            else:
                if res['payload'] is not None:
                    tasks.append(res['payload'])
        # TODO return 'ok': False when?
        return {'ok': True, 'payload': tasks, 'messages': messages}

    def getIssue(self, iid, **kwargs):
        """ Return issue for the given iid """
        self.logger.debug("getIssue(%s)", iid)
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

    # TODO move to an external library?
    def getObjectId(self, id):
        """ Return an ObjectId for the given id """
        self.logger.debug("getObjectId(%s)", id)
        if not isinstance(id, bson.ObjectId):
            try:
                id = bson.ObjectId(id)
            except Exception as e:
                self.logger.exception(e)
                return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': id}

    def getListOfReadyTaskIds(self, approvedOnly=False, **kwargs):
        self.logger.debug("getListOfReadyTaskIds(%s)", approvedOnly)
        match = {'active': True, 'done': False, 'inProg': False}
        if approvedOnly:
            match['approved'] = True
        return self.getListOfTaskIds(match, **kwargs)

    def getListOfReadyWorkflowTaskIds(self, name, approvedOnly=False,
                                      **kwargs):
        self.logger.debug("getListOfReadyWorkflowTaskIds(%s,%s)", name,
                          approvedOnly)
        match = {'active': True, 'done': False, 'inProg': False,
                 'workflow': name}
        if approvedOnly:
            match['approved'] = True
        return self.getListOfTaskIds(match, **kwargs)

    def getListOfTaskIds(self, match={}, **kwargs):
        self.logger.debug("getListOfTaskIds(%s)", match)
        res = self.getListOfTasks(match, {'_id': 1}, **kwargs)
        if not res['ok']:
            return res
        return {'ok': True, 'payload': [t['_id'] for t in res['payload']]}

    def getListOfTasks(self, match={}, proj=None, **kwargs):
        self.logger.debug("getListOfTasks(%s,%s)", match, proj)
        try:
            if proj is not None:
                curs_queue = self.coll_queue.find(match, proj)
            else:
                curs_queue = self.coll_queue.find(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        # prune out tasks for which requesting user does not have
        # sufficient privileges
        tasks = []
        for t in curs_queue:
            if self._hasTaskPrivileges(t['_id'], 'r', **kwargs):
                tasks.append(t)
        return {'ok': True, 'payload': tasks}

    def getListOfWorkflows(self, **kwargs):
        self.logger.debug("getListOfWorkflows()")
        if 'admin' in kwargs['userDoc'].get('groups', []):
            query = {}
        else:
            query = {"$or": [{'public': True},
                             {'owner': kwargs['userDoc']['user']},
                             {'groups':
                                 {"$in": kwargs['userDoc'].get('groups',
                                                               [])}}]}
        try:
            curs_workflows = self.coll_workflows.find(query).sort(
                [("name", pymongo.ASCENDING)])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': [w for w in curs_workflows]}

    def getListOfWorkflowTasks(self, name, match={}, **kwargs):
        self.logger.debug("getListOfWorkflowTasks(%s)", name)
        match['active'] = True
        match['workflow'] = name
        return self.getListOfTasks(match, **kwargs)

    def getSupportIssue(self, iid, **kwargs):
        """ Return a SupportIssue for the given iid """
        self.logger.debug("getSupportIssue(%s)", iid)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']

        res = self.find_one(self.coll_issues, {'_id': iid})
        if not res['ok']:
            return res
        doc = res['payload']

        if doc is None:
            message = "issue '%s' not found" % iid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        issue = SupportIssue()
        issue.fromDoc(doc)
        return {'ok': True, 'payload': issue}

    def getTask(self, tid, **kwargs):
        """ Return the specified task """
        self.logger.debug("getTask(%s)", tid)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']

        res = self.find_one(self.coll_queue, {'_id': tid})
        if not res['ok']:
            return res
        task = res['payload']

        if task is None:
            message = "task '%s' not found" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': task}

    def _getTemplateIssueValue(self, var, issue, **kwargs):
        """ Return a value for the given template variable. A finite number of
        such template variables are supported and defined below """
        self.logger.debug("_getTemplateIssueValue(%s,%s)", var, issue)
        if var == "COMPANY":
            return {'ok': True, 'payload': issue.company}
        elif var == "SALES_REP":
            match = {'_id': issue.company}
            res = self.find_one(self.coll_companies, match)
            if not res['ok']:
                return res
            company = res['payload']

            if company is not None and 'sales' in company and\
                    company['sales'] is not None:
                sales = ['[~' + name['jira'] + ']' for name in company[
                    'sales']]
                return {'ok': True, 'payload': string.join(sales, ', ')}
        return {'ok': False, 'payload': None}

    def _getTemplateQueryValue(self, var, override={}, **kwargs):
        """ Return a value for the given template variable. A finite number of
        such template variables are supported and defined below """
        # NOTE we are purposefully using local time here with now(); if there
        # is a need for explicit zulu time we can add those values separately
        self.logger.debug("_getTemplateQueryValue(%s,%s)", var, override)
        if var in override:
            return {'ok': True, 'payload': override[var]}

        if var == "DATE_NOW":
            payload = datetime.now()
            return {'ok': True, 'payload': bson.json_util.dumps(payload)}
        elif var.startswith("DATE_P"):
            deltaString = var.split("DATE_", 1)[1]
            try:
                delta = isodate.parse_duration(deltaString)
            except Exception as e:
                self.logger.exception(e)
                delta = timedelta(0)
            payload = datetime.now() - delta
            return {'ok': True, 'payload': bson.json_util.dumps(payload)}
        elif var == "DATE_1HOURAGO":
            payload = datetime.now()+timedelta(hours=-1)
            return {'ok': True, 'payload': bson.json_util.dumps(payload)}
        elif var == "DATE_1DAYAGO":
            payload = datetime.now()+timedelta(days=-1)
            return {'ok': True, 'payload': bson.json_util.dumps(payload)}
        elif var == "DATE_1WEEKAGO":
            payload = datetime.now()+timedelta(weeks=-1)
            return {'ok': True, 'payload': bson.json_util.dumps(payload)}
        elif var == "CURRENT_USER":
            return {'ok': True, 'payload': kwargs['userDoc']['user']}
        return {'ok': False, 'payload': None}

    def getUser(self, _id, **kwargs):
        """ Return the associated user document """
        self.logger.debug("getUser(%s)", _id)
        res = self.find_one(self.coll_users, {'_id': _id})
        if not res['ok']:
            return res
        user = res['payload']

        if user is None:
            message = "user '%s' not found" % _id
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': user}

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

    def getWorkflow(self, workflowName, **kwargs):
        """ Return the specified workflow """
        self.logger.debug("getWorkflow(%s)", workflowName)
        res = self.find_one(self.coll_workflows, {'name': workflowName})
        if not res['ok']:
            return res
        workflow = res['payload']

        if workflow is None:
            message = "workflow '%s' not found" % workflowName
            self.logger.warning(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': workflow}

    def getWorkflowsInSet(self, setname, **kwargs):
        """ Return the workflows in the specified set """
        self.logger.debug("getWorkflowsInSet(%s)", setname)
        match = {'sets': setname}
        try:
            curr = self.coll_workflows.find(match, {'_id': 0, 'name': 1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        res = [doc['name'] for doc in curr]
        return {'ok': True, 'payload': res}

    def healthcheck(self, **kwargs):
        """ Perform various sanity checks on the system """
        isOk = True
        messages = []
        # Are we locked out of MongoDB?
        if self.mongo.is_locked is True:
            isOk = False
            messages.append("karakuri: mongo is locked, no write access")
        # Can we read from the collections we care about?
        try:
            self.coll_issues.find_one({}, {'_id': 1})
            self.coll_companies.find_one({}, {'_id': 1})
            self.coll_workflows.find_one({}, {'_id': 1})
            self.coll_log.find_one({}, {'_id': 1})
            self.coll_queue.find_one({}, {'_id': 1})
            self.coll_users.find_one({}, {'_id': 1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            isOk = False
            messages.append("karakuri: unable to read from mongo: %s" % e)
        # Can we access JIRA?
        res = self.jira._healthcheck()
        isOk *= res['ok']
        if res['payload'] is not None:
            messages.extend(res['payload'])
        # Can we access Salesforce?
        res = self.sfdc._healthcheck()
        isOk *= res['ok']
        if res['payload'] is not None:
            messages.extend(res['payload'])
        return {'ok': bool(isOk), 'payload': messages}

    def loadJson(self, string):
        """ Return a JSON-validated dict for the string """
        self.logger.debug("loadJson(%s)", string)
        try:
            res = bson.json_util.loads(string)
        except Exception as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': res}

    def _log(self, tid, action, success, **kwargs):
        """ Log to karakuri.log <-- that's a collection! """
        self.logger.debug("log(%s,%s,%s)", tid, action, success)
        res = self.getObjectId(tid)
        if not res['ok']:
            return None
        tid = res['payload']

        res = self.getTask(tid)
        if not res['ok']:
            return None
        task = res['payload']

        _id = task['id']
        iid = task['iid']
        workflow = task['workflow']
        company = task['company']

        lid = bson.ObjectId()

        if 'userDoc' in kwargs:
            user = kwargs['userDoc']['user']
        else:
            user = None

        log = {'_id': lid, 'ns': task['ns'], 'id': _id, 'tid': tid, 'iid': iid,
               'workflow': workflow, 'action': action, 'p': success,
               'user': user, 'company': company}

        try:
            self.coll_log.insert(log)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            # TODO write to file on disk instead
        return lid

    def _processAction(self, action, issue, **kwargs):
        """ Do it like they do on the discovery channel """
        self.logger.debug("_processAction(%s,%s)", action['name'], issue)
        # Action must be defined somewhere
        if action['name'] != "sendEmail" and\
                not hasattr(self.issuer, action['name']) and\
                not hasattr(self.jira, action['name']) and\
                not hasattr(self.sfdc, action['name']):
            message = "'%s' is not a supported action" % action['name']
            self.logger.exception(message)
            return {'ok': False, 'payload': message}

        args = list(action.get('args', []))

        # Replace template variables with real values. A template variable is
        # identified as capital letters between double square brackets
        pattern = re.compile('\[\[([0-9A-Z_]+)\]\]')
        newargs = []
        for arg in args:
            # Use a set to remove repeats
            matches = set(pattern.findall(arg))
            for match in matches:
                res = self._getTemplateIssueValue(match, issue, **kwargs)
                if not res['ok']:
                    return res
                val = res['payload']
                arg = arg.replace('[[%s]]' % match, val)
            newargs.append(arg)

        # For the sake of logging reduce string arguments
        # to 50 characters and replace \n with \\n
        argString = (', '.join('"' + arg[:50].replace('\n',
                     '\\n') + '"' for arg in newargs))
        self.logger.info("%s(%s)", action['name'], argString)

        # Send an email with AWS SES
        if action['name'] == "sendEmail":
            if len(newargs) != 4:
                return {'ok': False,
                        'payload': 'sendEmail requires four arguments, '
                        'but %i specified' % len(newargs)}
            return self._sendEmail(newargs[0], newargs[1], newargs[2],
                                   newargs[3])

        # Priority goes to the issuer, as there can be only one. If the issuer
        # has the method it will execute it and that's it. Otherwise any other
        # other library that has the method will execute it.
        if hasattr(self.issuer, action['name']):
            if self.issuer == self.jira:
                # First argument to jira++ is a jira key
                newargs.insert(0, issue.key)
                return self._processJiraAction(action, newargs, **kwargs)
            elif self.issuer == self.sfdc:
                # First argument to sfdc++ is a companyId
                newargs.insert(0, issue.company)
                return self._processSfdcAction(action, newargs, **kwargs)
            else:
                return self._processIssuerAction(action, newargs, **kwargs)

        results = []
        if hasattr(self.jira, action['name']):
            # First argument to jira++ is a jira key
            newargs.insert(0, issue.key)
            results.append(self._processJiraAction(action, newargs, **kwargs))

        if hasattr(self.sfdc, action['name']):
            # First argument to sfdc++ is a companyId
            newargs.insert(0, issue.company)
            results.append(self._processSfdcAction(action, newargs, **kwargs))

        res = {'ok': True, 'payload': []}
        for r in results:
            res['ok'] *= r['ok']
            res['payload'].append(r['payload'])
        return res

    def _processIssuerAction(self, action, args, **kwargs):
        if self.live:
            method = getattr(self.issuer, action['name'])
            # expand list to function arguments
            res = method(*args)
        else:
            # simulate success
            res = {'ok': True, 'payload': True}
        return res

    def _processJiraAction(self, action, args, **kwargs):
        self.logger.debug("_processJiraAction(%s,%s)", action, args)
        if self.live:
            method = getattr(self.jira, action['name'])
            # expand list to function arguments
            res = method(*args)
        else:
            # simulate success
            res = {'ok': True, 'payload': {'key': 'CS-XXXXX',
                                           'updated': datetime.utcnow()}}
        return res

    def _processSfdcAction(self, action, args, **kwargs):
        if self.live:
            method = getattr(self.sfdc, action['name'])
            # expand list to function arguments
            res = method(*args)
        else:
            # simulate success
            res = {'ok': True, 'payload': True}
        return res

    def processTask(self, tid, **kwargs):
        """ Process the specified task """
        self.logger.debug("processTask(%s)", tid)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']

        res = self.getTask(tid, **kwargs)
        if not res['ok']:
            return res
        task = res['payload']

        # do not process a task whose start date is in the future
        if task['start'] > datetime.utcnow():
            message = "start time in the future, skipping %s" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}

        if self._amiThrottling(approvedBy=task['approvedBy'],
                               company=task['company'], **kwargs):
            message = "processing limit reached, skipping %s" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}

        # validate that this is still worth running
        res = self.validateTask(tid, **kwargs)
        # whether or not validateTask ran
        if not res['ok']:
            return res
        # whether or not the task is validated
        if not res['payload']:
            return {'ok': False, 'payload': 'validation failed'}

        match = {'_id': tid, 'active': True, 'done': False, 'inProg': False,
                 'approved': True}
        updoc = {"$set": {'inProg': True}}
        res = self.find_and_modify_task(match, updoc)
        if not res['ok']:
            return res
        task = res['payload']

        if task is None:
            # most likely the task hasn't been approved
            message = "unable to put task '%s' in to progress" % tid
            self.logger.warning(message)
            return {'ok': False, 'payload': message}

        res = self.processWorkflowActions(tid, task['id'], task['workflow'],
                                          task['iid'], **kwargs)
        lid = self._log(tid, 'process', res['ok'], **kwargs)
        if not res['ok']:
            return res

        # Success! Get the issuer last updated time since we'll be comparing
        # future workflow queries to that
        updated = res['payload'].get('updated')

        if self.live:
            match = {'_id': task['id']}
            updoc = {'$push': {'karakuri.workflows_performed':
                               {'name': task['workflow'], 'lid': lid}},
                     '$addToSet': {'karakuri.active_states':
                                   {'name': task['workflow'],
                                    'updated': updated}}}
            ns = task['ns']
            if ns == "support.issues":
                res = self.find_and_modify_issue(match, updoc)
            else:
                (db, coll) = ns.split('.')
                res = self.find_and_modify(self.mongo[db][coll], match, updoc)

            if not res['ok'] or res['payload'] is None:
                message = "unable to record workflow '%s' in doc '%s'"\
                    % (task['workflow'], task['id'])
                self.logger.exception(message)
                self._log(tid, 'record', False, **kwargs)
                return {'ok': False, 'payload': message}
            self._log(tid, 'record', True, **kwargs)

        match = {'_id': tid}
        updoc = {"$set": {'done': True, 'inProg': False}}
        res = self.find_and_modify_task(match, updoc)
        if not res['ok']:
            return res
        task = res['payload']

        if task is None:
            message = "unable to take task %s out of progress" % tid
            self.logger.exception(message)
            return {'ok': False, 'payload': message}
        return {'ok': True, 'payload': task}

    def processWorkflowActions(self, tid, _id, workflowName, iid, **kwargs):
        """ Perform the specified workflow for the given doc """
        self.logger.info("processWorkflowActions(%s,%s,%s)", _id, workflowName,
                         iid)
        res = self.getObjectId(_id)
        if not res['ok']:
            return res
        _id = res['payload']

        if iid is not None:
            res = self.getSupportIssue(iid, **kwargs)
            if not res['ok']:
                return res
            issue = res['payload']
        else:
            issue is None

        res = self.getWorkflow(workflowName, **kwargs)
        if not res['ok']:
            return res
        workflow = res['payload']

        if workflow is None:
            message = "unable to get workflow '%s'" % workflowName
            self.logger.exception(message)
            return {'ok': False, 'payload': message}

        if 'actions' in workflow:
            for action in workflow['actions']:
                if issue is not None:
                    res = self._processAction(action, issue, **kwargs)
                    self._log(tid, action['name'], res['ok'], **kwargs)

                    if not res['ok']:
                        return res
        # res is the result of the last action, which contains the key acted
        # upon and the last updated time as reported by the issuer
        return res

    def pruneTask(self, tid, **kwargs):
        """ Remove task if it fails validation """
        self.logger.debug("pruneTask(%s)", tid)
        res = self.validateTask(tid, **kwargs)
        if not res['ok']:
            return res
        if not res['payload']:
            res = self.removeTask(tid, **kwargs)
        else:
            res['payload'] = None
        return res

    def queueTask(self, tid, ns, _id, workflowName, iid=None, key=None,
                  company=None, **kwargs):
        """ Create a task for the given doc and workflow """
        # TODO move iid, key, company into some ns-specific meta doc
        self.logger.info("queueTask(%s,%s,%s,%s,%s,%s,%s)", tid, ns, _id,
                         workflowName, iid, key, company)
        res = self.getObjectId(_id)
        if not res['ok']:
            return res
        _id = res['payload']

        # don't queue a task that is already queued
        match = {'id': _id, 'workflow': workflowName, 'active': True,
                 'done': False}
        if self.coll_queue.find(match).count() != 0:
            self.logger.warning("workflow '%s' already queued for doc '%s', "
                                "skipping", workflowName, _id)
            return {'ok': True, 'payload': None}

        now = datetime.utcnow()

        # is the workflow auto-approved?
        res = self.getWorkflow(workflowName)
        if not res['ok']:
            return res
        wf = res['payload']
        approved = wf.get('auto_approve', False)

        task = {'_id': tid, 'ns': ns, 'id': _id, 'iid': iid, 'key': key,
                'company': company, 'workflow': workflowName,
                'approved': approved, 'done': False, 'inProg': False, 't': now,
                'start': now, 'active': True,
                'createdBy': kwargs['userDoc']['user']}

        # karakuri approves, that's who!
        if approved is True:
            task['approvedBy'] = 'karakuri'

        try:
            self.coll_queue.insert(task)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': task}

    def removeTask(self, tid, **kwargs):
        """ Remove the task from the queue """
        self.logger.debug("removeTask(%s)", tid)
        updoc = {"$set": {'active': False}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'remove', res['ok'], **kwargs)
        return res

    def _sendEmail(self, fromAddress, toAddresses, subject, body):
        """ Send an email using the AWS SES service """
        self.logger.debug("_sendEmail(%s, %s, %s, %s)", fromAddress,
                          toAddresses, subject, body)

        # Expect toAddresses to be a comma delimitted string of email addresses
        # Turn it into an array of email addresses for the SESHandler
        toAddresses = [email.strip() for email in toAddresses.split(',')]

        if self.live:
            try:
                ses = SESHandler(self.args['aws_key'], self.args['aws_secret'],
                                 fromAddress, toAddresses, subject)
            except Exception as e:
                self.logger.exception(e)
                return {'ok': False, 'payload': e}

            rec = logging.makeLogRecord({'msg': body})
            try:
                res = ses.emit(rec)
            except Exception as e:
                self.logger.exception(e)
                return {'ok': False, 'payload': e}
            return {'ok': True, 'payload': res}
        else:
            # simulate success
            return {'ok': True, 'payload': True}

    def setIssuer(self, issuer):
        """ Set issue tracking system """
        self.issuer = issuer

    def setJira(self, jira):
        """ Set JIRA """
        self.jira = jira

    def setSfdc(self, sfdc):
        """ Set SFDC """
        self.sfdc = sfdc

    def sleepIssue(self, iid, seconds, **kwargs):
        """ Sleep the issue """
        self.logger.debug("sleepIssue(%s)", iid)
        seconds = int(seconds)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        updoc = {"$set": {'karakuri.sleep': wakeDate}}
        return self.updateIssue(iid, updoc, **kwargs)

    def sleepTask(self, tid, seconds, **kwargs):
        """ Sleep the task, i.e. assign a wake date """
        self.logger.debug("sleepTask(%s)", tid)
        seconds = int(seconds)
        now = datetime.utcnow()

        if seconds > (datetime.max-now).total_seconds():
            wakeDate = datetime.max
        else:
            diff = timedelta(seconds=seconds)
            wakeDate = now + diff

        updoc = {"$set": {'start': wakeDate}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'sleep', res['ok'], **kwargs)
        return res

    def throttleRefresh(self, **kwargs):
        oneDayAgo = datetime.utcnow()+timedelta(days=-1)
        # tasks processed successfully in the last day
        match = {"_id": {"$gt": bson.ObjectId.from_datetime(oneDayAgo)},
                 "action": "process", "p": True}
        proj = {'tid': 1, 'company': 1}

        try:
            curr_docs = self.coll_log.find(match, proj)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        processedTids = []
        # re-init
        self.throttle['companies'] = {}
        for doc in curr_docs:
            processedTids.append(doc['tid'])
            if doc['company'] in self.throttle['companies']:
                self.throttle['companies'][doc['company']] += 1
            else:
                self.throttle['companies'][doc['company']] = 1
        self.throttle['global'] = len(processedTids)
        self.logger.info("global throttle set to %i", self.throttle['global'])
        for company in self.throttle['companies']:
            self.logger.info("throttle for company '%s' set to %i", company,
                             self.throttle['companies'][company])

        # determine which users approved these tasks
        # NOTE it's possible to overcount approvals here
        match = {"$match": {"tid": {"$in": processedTids}, "action": "approve",
                 "p": True}}
        group = {"$group": {"_id": "$user", "count": {"$sum": 1}}}
        project = {"$project": {"user": "$_id", "count": "$count", "_id": 0}}

        try:
            res = self.coll_log.aggregate([match, group, project])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if res['ok']:
            users = res['result']
            # re-init
            self.throttle['users'] = {}
            for user in users:
                self.throttle['users'][user['user']] = user['count']
                self.logger.info("throttle for user '%s' set to %i",
                                 user['user'], user['count'])

    def updateIssue(self, iid, updoc, **kwargs):
        """ They see me rollin' """
        self.logger.debug("updateIssue(%s,%s)", iid, updoc)
        res = self.getObjectId(iid)
        if not res['ok']:
            return res
        iid = res['payload']
        match = {'_id': iid}
        return self.find_and_modify_issue(match, updoc)

    def updateTask(self, tid, updoc, **kwargs):
        """ They hatin' """
        self.logger.debug("updateTask(%s,%s)", tid, updoc)
        res = self.getObjectId(tid)
        if not res['ok']:
            return res
        tid = res['payload']
        match = {'_id': tid}
        return self.find_and_modify_task(match, updoc)

    def updateUser(self, uid, updoc, **kwargs):
        """ Update an existing user """
        self.logger.debug("updateUser(%s,%s)", uid, updoc)
        res = self.getObjectId(uid)
        if not res['ok']:
            return res
        uid = res['payload']
        match = {'_id': uid}
        return self.find_and_modify_user(match, updoc)

    def updateWorkflow(self, name, fields, **kwargs):
        """ Update an existing workflow """
        self.logger.debug("updateWorkflow(%s,%s)", name, fields)
        if "$set" not in fields:
            updoc = {"$set": fields}
        else:
            updoc = fields

        res = self.getWorkflow(name, **kwargs)
        if not res['ok']:
            return res
        workflow = res['payload']
        oldworkflow = copy.deepcopy(workflow)

        for key in updoc["$set"]:
            workflow[key] = updoc["$set"][key]

        # only admins can change auto-approve
        if workflow.get('auto_approve', "") !=\
                oldworkflow.get('auto_approve', "") and\
                'admin' not in kwargs['userDoc']['groups']:
            return {'ok': False,
                    'payload': "only admins can set auto-approve"}

        # validate the workflow to be
        res = self.validateWorkflow(workflow, **kwargs)
        if not res['ok']:
            return res

        match = {'name': name}
        return self.find_and_modify_workflow(match, updoc)

    def validateTask(self, tidORtask, cleanStates=True, **kwargs):
        """ Validate the task, i.e. that the doc satisfies the requirements
        of the workflow """
        self.logger.debug("validateTask(%s,%s)", tidORtask, cleanStates)
        if isinstance(tidORtask, dict):
            task = tidORtask
            tid = task['_id']
        else:
            tid = tidORtask
            res = self.getTask(tid, **kwargs)
            if not res['ok']:
                return res
            task = res['payload']

        _id = task['id']
        workflowName = task['workflow']

        res = self.getWorkflow(workflowName, **kwargs)
        if not res['ok']:
            return res
        workflow = res['payload']

        res = self.buildValidateQuery(workflow, _id, task=task, **kwargs)
        if not res['ok']:
            return res
        match = res['payload']

        # the doc collection
        ns = workflow['ns']
        (db, coll) = ns.split('.')

        try:
            doc = self.mongo[db][coll].find_one(match)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        if doc is None:
            res = False
        else:
            res = True
            # Cleanup outdated active states and revalidate
            # Otherwise, for each set of the workflow, if the doc is in a
            # state of the set that is not a prereq of the workflow, continue
            kdoc = doc.get('karakuri')
            if kdoc is not None:
                activeStates = kdoc.get('active_states')
                if activeStates is not None:
                    if cleanStates is True:
                        for state in activeStates:
                            # TODO generalize this away from jira
                            if 'jira' in doc:
                                if doc['jira']['fields']['updated'] >\
                                        state.get('updated'):
                                    # Remove this state from active states
                                    match = {'_id': doc['_id']}
                                    updoc = {"$pull":
                                             {'karakuri.active_states':
                                              {'name': state.get('name')}}}
                                    try:
                                        self.mongo[db][coll].\
                                            update(match, updoc)
                                    except pymongo.errors.PyMongoError\
                                            as e:
                                        self.logger.exception(e)
                                        return {'ok': False,
                                                'payload': e}
                        return self.validateTask(task, False, **kwargs)
                    else:
                        sets = workflow['sets']
                        prereqs = [prereq['name'] for prereq in
                                   workflow['prereqs']]
                        for aset in sets:
                            res = self.getWorkflowsInSet(aset)
                            if not res['ok']:
                                return res
                            workflowsInSet = res['payload']
                            for state in activeStates:
                                # Is the doc in a state of the set that is not
                                # a prereq of this workflow?
                                if state.get('name') in workflowsInSet and\
                                        state.get('name') not in prereqs:
                                    res = False
                                    break
                            if res is False:
                                break

        self._log(tid, "validate", True, **kwargs)
        if res:
            self.logger.debug("task validated!")
        else:
            self.logger.debug("task !validated")
        return {'ok': True, 'payload': res}

    def validateWorkflow(self, workflow, **kwargs):
        self.logger.debug("validateWorkflow(%s)", workflow)
        if not isinstance(workflow, dict):
            return {'ok': False, 'payload': 'workflow is not of type dict'}
        if 'name' not in workflow:
            return {'ok': False, 'payload': "workflow missing 'name'"}
        if 'ns' not in workflow:
            return {'ok': False, 'payload': "workflow missing 'ns'"}
        if 'query_string' not in workflow:
            return {'ok': False, 'payload': "workflow missing 'query_string'"}
        # primary query must have join key if it's not the only query
        if 'ns1' in workflow:
            if 'join_key' not in workflow:
                return {'ok': False, 'payload': "workflow missing 'join_key'"}
        i = 1
        while ('ns%s' % i) in workflow:
            if ('ns%s' % i) not in workflow:
                return {'ok': False, 'payload': "workflow missing 'ns%s'" % i}
            if ('query_string%s' % i) not in workflow:
                return {'ok': False,
                        'payload': "workflow missing 'query_string%s'" % i}
            if ('join_key%s' % i) not in workflow:
                return {'ok': False,
                        'payload': "workflow missing 'join_key%s'" % i}
            i += 1
        return {'ok': True, 'payload': workflow}

    def wakeIssue(self, iid, **kwargs):
        """ Wake the issue """
        self.logger.debug("wakeIssue(%s)", iid)
        updoc = {"$unset": {'karakuri.sleep': ""}}
        return self.updateIssue(iid, updoc, **kwargs)

    def wakeTask(self, tid, **kwargs):
        """ Wake the task, i.e. mark it ready to go """
        self.logger.debug("wakeTask(%s)", tid)
        updoc = {"$set": {'start': datetime.utcnow()}}
        res = self.updateTask(tid, updoc, **kwargs)
        self._log(tid, 'sleep', res['ok'], **kwargs)
        return res

    def start(self):
        """ Start the RESTful interface """
        self.logger.debug("start()")
        self.logger.info("karakuri is at REST")

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
                token = auth_dict.get('kk_token', None)

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
            ret = {'status': 'success', 'data': data}
            bottle.response.status = 200
            bottle.response.add_header("Content-Encoding", "gzip")
            content = bson.json_util.dumps(ret)
            compressed = StringIO.StringIO()
            with gzip.GzipFile(fileobj=compressed, mode='w') as f:
                f.write(content)
            return compressed.getvalue()

        def fail(data=None):
            ret = {'status': 'fail', 'data': data}
            bottle.response.status = 403
            return bson.json_util.dumps(ret)

        def error(message=None):
            ret = {'status': 'error', 'message': str(message)}
            bottle.response.status = 403
            return bson.json_util.dumps(ret)

        # These are the RESTful API endpoints. There are many like it, but
        # these are them

        @b.post('/issue')
        @authenticated
        def issue_create(**kwargs):
            body = bottle.request.body.read()

            res = self.loadJson(body)
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.createIssue(fields, **kwargs)
            if res['ok']:
                return success({'issue': res['payload']})
            return error(res['payload'])

        @b.route('/issue/<id>')
        @authenticated
        def issue_get(id, **kwargs):
            return issue_response(self.getIssue, id, **kwargs)

        @b.route('/issue')
        @authenticated
        def issue_list(**kwargs):
            # TODO implement no-way, Jose 404
            return fail()

        def issue_response(method, id, **kwargs):
            res = method(id, **kwargs)
            if res['ok']:
                return success({'issue': res['payload']})
            return error(res['payload'])

        @b.route('/issue/<id>/sleep')
        @b.route('/issue/<id>/sleep/<seconds:int>')
        @authenticated
        def issue_sleep(id, seconds=sys.maxint, **kwargs):
            """ Sleep the issue. A sleeping issue cannot have tasks queued """
            self.logger.debug("issue_sleep(%s,%s)", id, seconds)
            return issue_response(self.sleepIssue, id, seconds=seconds,
                                  **kwargs)

        @b.route('/issue/<id>/wake')
        @authenticated
        def issue_wake(id, **kwargs):
            """ Wake the issue, i.e. unsleep it """
            self.logger.debug("issue_wake(%s)", id)
            return issue_response(self.wakeIssue, id, **kwargs)

        @b.route('/monitor')
        def monitor(**kwargs):
            """ Check essential services and ack their status """
            self.logger.debug("health()")
            ret = {'status': 'unsure', 'messages': []}
            res = self.healthcheck(**kwargs)
            if res['ok'] is True:
                ret['messages'].\
                    append('Healthy as a fox, thanks for checking!')
                ret['status'] = 'OK'
            else:
                ret['status'] = 'bad'
            if res['payload'] is not None:
                ret['messages'].extend(res['payload'])
            return bson.json_util.dumps(ret)

        @b.route('/queue/approve')
        @authenticated
        def queue_approve(**kwargs):
            """ Approve all ready tasks """
            self.logger.debug("queue_approve()")
            return queue_response(self.approveTask, **kwargs)

        @b.route('/queue/disapprove')
        @authenticated
        def queue_disapprove(**kwargs):
            """ Disapprove all ready tasks """
            self.logger.debug("queue_disapprove()")
            return queue_response(self.disapproveTask, **kwargs)

        @b.route('/queue/find')
        @authenticated
        def queue_find(**kwargs):
            """ Find and queue new tasks """
            self.logger.debug("queue_find()")
            res = self.findTasks(**kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/queue')
        @b.route('/task')
        @authenticated
        def queue_list(**kwargs):
            """ Return a list of all active tasks """
            self.logger.debug("queue_list()")
            match = {'active': True}
            res = self.getListOfTasks(match, **kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/queue/process')
        @authenticated
        def queue_process(**kwargs):
            """ Process all ready tasks """
            self.logger.debug("queue_process()")
            return queue_response(self.processTask, approvedOnly=True,
                                  **kwargs)

        @b.route('/queue/prune')
        @authenticated
        def queue_prune(**kwargs):
            """ Prune all ready tasks """
            self.logger.debug("queue_prune()")
            return queue_response(self.pruneTask, **kwargs)

        @b.route('/queue/remove')
        @authenticated
        def queue_remove(**kwargs):
            """ Remove all ready tasks """
            self.logger.debug("queue_remove()")
            return queue_response(self.removeTask, **kwargs)

        def queue_response(method, **kwargs):
            self.logger.debug("queue_response(%s)", method.__name__)
            res = self.getListOfReadyTaskIds(**kwargs)
            if res['ok']:
                res = self.forListOfTaskIds(method, res['payload'], **kwargs)
                if res['ok']:
                    # TODO res may contain 'messages' as well from failed tasks
                    return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/queue/sleep')
        @b.route('/queue/sleep/<seconds:int>')
        @authenticated
        def queue_sleep(seconds=sys.maxint, **kwargs):
            """ Sleep all ready tasks """
            self.logger.debug("queue_sleep(%s)", seconds)
            return queue_response(self.sleepTask, seconds=seconds, **kwargs)

        @b.route('/queue/wake')
        @authenticated
        def queue_wake(**kwargs):
            """ Wake all ready tasks """
            self.logger.debug("queue_wake()")
            return queue_response(self.wakeTask, **kwargs)

        @b.route('/task/<id>/approve')
        @authenticated
        def task_approve(id, **kwargs):
            """ Approve the task """
            self.logger.debug("task_approve(%s)", id)
            return task_response(self.approveTask, id, **kwargs)

        @b.route('/task/<id>/disapprove')
        @authenticated
        def task_disapprove(id, **kwargs):
            """ Disapprove the task """
            self.logger.debug("task_disapprove(%s)", id)
            return task_response(self.disapproveTask, id, **kwargs)

        @b.route('/task/<id>')
        @authenticated
        def task_get(id, **kwargs):
            """ Return the task """
            self.logger.debug("task_get(%s)", id)
            return task_response(self.getTask, id, **kwargs)

        @b.route('/task/<id>/process')
        @authenticated
        def task_process(id, **kwargs):
            """ Process the task """
            self.logger.debug("task_process(%s)", id)
            return task_response(self.processTask, id, approvedOnly=True,
                                 **kwargs)

        @b.route('/task/<id>/prune')
        @authenticated
        def task_prune(id, **kwargs):
            """ Prune the task """
            self.logger.debug("task_prune(%s)", id)
            return task_response(self.pruneTask, id, **kwargs)

        @b.route('/task/<id>/remove')
        @authenticated
        def task_remove(id, **kwargs):
            """ Remove the task """
            self.logger.debug("task_remove(%s)", id)
            return task_response(self.removeTask, id, **kwargs)

        def task_response(method, id, **kwargs):
            self.logger.debug("task_response(%s,%s)", method.__name__, id)
            res = method(id, **kwargs)
            if res['ok']:
                return success({'task': res['payload']})
            return error(res['payload'])

        @b.route('/task/<id>/sleep')
        @b.route('/task/<id>/sleep/<seconds:int>')
        @authenticated
        def task_sleep(id, seconds=sys.maxint, **kwargs):
            """ Sleep the task. A sleeping task cannot be processed """
            self.logger.debug("task_sleep(%s,%s)", id, seconds)
            return task_response(self.sleepTask, id, seconds=seconds, **kwargs)

        @b.route('/task/<id>/wake')
        @authenticated
        def task_wake(id, **kwargs):
            """ Wake the task, i.e. unsleep it """
            self.logger.debug("task_wake(%s)", id)
            return task_response(self.wakeTask, id, **kwargs)

        @b.route('/user/<id>')
        @authenticated
        def user_get(id, **kwargs):
            """ Return the user """
            self.logger.debug("user_get(%s)", id)
            return user_response(self.getUser, id, **kwargs)

        @b.post('/user/<uid>/workflow/<workflow>')
        @authenticated
        def user_add_workflow(uid, workflow, **kwargs):
            """ Add user workflow """
            self.logger.debug("user_add_workflow(%s,%s)", uid, workflow)
            try:
                uid = bson.json_util.loads(uid)
            except ValueError as e:
                self.logger.exception(e)
                return error(str(e))
            updoc = {"$addToSet": {'workflows': workflow}}
            return user_response(self.updateUser, uid, updoc, **kwargs)

        @b.delete('/user/<uid>/workflow/<workflow>')
        @authenticated
        def user_remove_workflow(uid, workflow, **kwargs):
            """ Remove user workflow """
            self.logger.debug("user_remove_workflow(%s,%s)", uid, workflow)
            try:
                uid = bson.json_util.loads(uid)
            except ValueError as e:
                self.logger.exception(e)
                return error(str(e))
            updoc = {"$pull": {'workflows': workflow}}
            return user_response(self.updateUser, uid, updoc, **kwargs)

        @b.post('/login')
        def user_login(**kwargs):
            """ Find a user with the specified auth_token """
            self.logger.debug("user_login()")
            token = bottle.request.params.get('kk_token')
            if 'kk_token' in bottle.request.params:
                token = bottle.request.params['kk_token']
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

        def user_response(method, id, *args, **kwargs):
            self.logger.debug("user_response(%s,%s)", method.__name__, id)
            res = method(id, *args, **kwargs)
            if res['ok']:
                return success({'user': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<wfname>/addtoset/<setname>')
        @authenticated
        def add_workflow_to_set(wfname, setname, **kwargs):
            match = {'name': wfname}
            updoc = {"$addToSet": {'sets': setname}}
            res = self.find_and_modify_workflow(match, updoc)
            if res['ok']:
                return success(res['payload'])
            return error(res['payload'])

        @b.route('/workflow/<wfname>/rmfromset/<setname>')
        @authenticated
        def rm_workflow_from_set(wfname, setname, **kwargs):
            match = {'name': wfname}
            updoc = {"$pull": {'sets': setname}}
            res = self.find_and_modify_workflow(match, updoc)
            if res['ok']:
                return success(res['payload'])
            return error(res['payload'])

        @b.route('/workflow/<name>/approve')
        @authenticated
        def workflow_approve(name, **kwargs):
            """ Approve all ready tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'e', **kwargs):
                return error("Insufficient privileges")
            return workflow_response(self.approveTask, name, **kwargs)

        @b.post('/workflow')
        @authenticated
        def workflow_create(**kwargs):
            """ Create a workflow """
            body = bottle.request.body.read()

            res = self.loadJson(body)
            if not res['ok']:
                return res
            fields = res['payload']

            res = self.createWorkflow(fields, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.delete('/workflow/<name>')
        @authenticated
        def workflow_delete(name, **kwargs):
            """ Delete the workflow """
            self.logger.debug("workflow_delete(%s)", name)
            if not self._hasWorkflowPrivileges(name, 'w', **kwargs):
                return error("Insufficient privileges")
            res = self.deleteWorkflow(name, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/disapprove')
        @authenticated
        def workflow_disapprove(name, **kwargs):
            """ Disapprove all ready tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'e', **kwargs):
                return error("Insufficient privileges")
            return workflow_response(self.disapproveTask, name, **kwargs)

        @b.route('/workflow/<name>/find')
        @authenticated
        def workflow_find(name, **kwargs):
            """ Find and queue new tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'r', **kwargs):
                return error("Insufficient privileges")
            res = self.findWorkflowTasks(name, **kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/issues')
        @authenticated
        def workflow_issues(name, **kwargs):
            """ Find and queue new tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'r', **kwargs):
                return error("Insufficient privileges")
            res = self.findWorkflowTasksIssues(name, **kwargs)
            if res['ok']:
                return success({'issues': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/issuesummaries')
        @authenticated
        def workflow_issuesummaries(name, **kwargs):
            """ Find and queue new tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'r', **kwargs):
                return error("Insufficient privileges")
            res = self.findWorkflowTasksIssuesSummaries(name, **kwargs)
            if res['ok']:
                return success({'issues': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>')
        @authenticated
        def workflow_get(name, **kwargs):
            """ Return the workflow """
            if not self._hasWorkflowPrivileges(name, 'r', **kwargs):
                return error("Insufficient privileges")
            res = self.getWorkflow(name, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.route('/workflow')
        @authenticated
        def workflow_list(**kwargs):
            """ Return a list of workflows """
            self.logger.debug("workflow_list()")
            res = self.getListOfWorkflows(**kwargs)
            if res['ok']:
                return success({'workflows': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/process')
        @authenticated
        def workflow_process(name, **kwargs):
            """ Process all ready tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'e', **kwargs):
                return error("Insufficient privileges")
            self.logger.debug("workflow_process(%s)", name)
            return workflow_response(self.processTask, name, approvedOnly=True,
                                     **kwargs)

        @b.route('/workflow/<name>/queue')
        @authenticated
        def workflow_queue(name, **kwargs):
            """ Return tasks queued for the workflow """
            self.logger.debug("workflow_queue(%s)", name)
            if not self._hasWorkflowPrivileges(name, 'r', **kwargs):
                return error("Insufficient privileges")

            res = self.getWorkflow(name)
            if not res['ok']:
                return res
            wf = res['payload']

            if '[[CURRENT_USER]]' in wf['query_string']:
                # if workflow has user-specific reqs then we prune and find
                # them first
                # workflow_prune(name) and workflow_find(name)
                res = self.getListOfReadyWorkflowTaskIds(name, **kwargs)
                if res['ok']:
                    res = self.forListOfTaskIds(self.pruneTask, res['payload'], **kwargs)
                    if res['ok']:
                        pass
                        # TODO res may contain 'messages' as well from failed tasks
                res = self.findWorkflowTasks(name, **kwargs)
                if res['ok']:
                    pass
                match = {'createdBy': kwargs['userDoc']['user']}
            else:
                match = {}

            res = self.getListOfWorkflowTasks(name, match, **kwargs)
            if res['ok']:
                return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/prune')
        @authenticated
        def workflow_prune(name, **kwargs):
            """ Prune all ready tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'e', **kwargs):
                return error("Insufficient privileges")
            self.logger.debug("workflow_prune(%s)", name)
            return workflow_response(self.pruneTask, name, **kwargs)

        @b.route('/workflow/<name>/remove')
        @authenticated
        def workflow_remove(name, **kwargs):
            """ Remove all ready tasks for the workflow """
            if not self._hasWorkflowPrivileges(name, 'e', **kwargs):
                return error("Insufficient privileges")
            self.logger.debug("workflow_remove(%s)", name)
            return workflow_response(self.removeTask, name, **kwargs)

        def workflow_response(method, name, **kwargs):
            self.logger.debug("workflow_response(%s,%s)", method.__name__,
                              name)
            res = self.getListOfReadyWorkflowTaskIds(name, **kwargs)
            if res['ok']:
                res = self.forListOfTaskIds(method, res['payload'], **kwargs)
                if res['ok']:
                    # TODO res may contain 'messages' as well from failed tasks
                    return success({'tasks': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/sleep')
        @b.route('/workflow/<name>/sleep/<seconds:int>')
        @authenticated
        def workflow_sleep(name, seconds=sys.maxint, **kwargs):
            """ Sleep all ready tasks for the workflow """
            self.logger.debug("workflow_sleep(%s,%s)", name, seconds)
            if not self._hasWorkflowPrivileges(name, 'e', **kwargs):
                return error("Insufficient privileges")
            return workflow_response(self.sleepTask, name, seconds=seconds,
                                     **kwargs)

        @b.post('/testworkflow')
        @authenticated
        def workflow_test(**kwargs):
            """ Return a list of tickets that satisfy the workflow reqs """
            self.logger.debug("workflow_test()")
            body = bottle.request.body.read()
            self.logger.debug("body: %s", body)

            res = self.loadJson(body)
            if not res['ok']:
                return res
            workflow = res['payload']

            res = self.validateWorkflow(workflow, **kwargs)
            if not res['ok']:
                return error(res['payload'])

            res = self.findWorkflowDocs(workflow, **kwargs)
            if res['ok']:
                return success({'ns': workflow['ns'], 'docs': res['payload']})
            return error(res['payload'])

        @b.post('/workflow/<name>')
        @authenticated
        def workflow_update(name, **kwargs):
            """ Update a workflow """
            self.logger.debug("workflow_update(%s)", name)
            if not self._hasWorkflowPrivileges(name, 'w', **kwargs):
                return error("Insufficient privileges")
            body = bottle.request.body.read()

            res = self.loadJson(body)
            if not res['ok']:
                return res
            workflow = res['payload']

            res = self.updateWorkflow(name, workflow, **kwargs)
            if res['ok']:
                return success({'workflow': res['payload']})
            return error(res['payload'])

        @b.route('/workflow/<name>/wake')
        @authenticated
        def workflow_wake(name, **kwargs):
            """ Wake all ready tasks for the workflow """
            self.logger.debug("workflow_wake(%s)", name)
            if not self._hasWorkflowPrivileges(name, 'e', **kwargs):
                return error("Insufficient privileges")
            return workflow_response(self.wakeTask, name, **kwargs)

        b.run(host=self.args['rest_host'], port=self.args['rest_port'])

if __name__ == "__main__":
    desc = "An automaton: http://en.wikipedia.org/wiki/Karakuri_ningy%C5%8D"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument("--jira-password", metavar="PASSWORD",
                               help="specify a JIRA password")
    parser.add_config_argument("--jira-username", metavar="USERNAME",
                               help="specify a JIRA username")
    parser.add_config_argument("--sfdc-password", metavar="SFDCPASSWORD",
                               help="specify a SFDC password")
    parser.add_config_argument("--sfdc-username", metavar="SFDCUSERNAME",
                               help="specify a SFDC username")
    parser.add_config_argument("--aws-key", metavar="AWSKEY",
                               help="specify an AWS key")
    parser.add_config_argument("--aws-secret", metavar="AWSSECRET",
                               help="specify an AWS secret")
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
    parser.add_config_argument("--rest-host", metavar="HOST",
                               default="localhost",
                               help="the RESTful interface host "
                               "(default=localhost)")
    parser.add_config_argument("--rest-port", metavar="PORT", default=8080,
                               type=int,
                               help="the RESTful interface port "
                                    "(default=8080)")
    parser.add_config_argument("--global-limit", metavar="NUMBER", type=int,
                               help="limit global process'ing to NUMBER tasks")
    parser.add_config_argument("--user-limit", metavar="NUMBER", type=int,
                               help="limit process'ing to NUMBER tasks per "
                                    "approving user")
    parser.add_config_argument("--company-limit", metavar="NUMBER", type=int,
                               help="limit process'ing to NUMBER tasks per "
                                    "customer")
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
        k = karakuri(args)

        # Initialize JIRA++
        jirapp = jirapp(args, k.mongo)
        jirapp._setLive(args.live)
        k.setJira(jirapp)

        # Initialize SFDC++
        sfdcpp = sfdcpp(args, k.mongo)
        sfdcpp._setLive(args.live)
        k.setSfdc(sfdcpp)

        # Set the Issuer. There can be only one:
        # https://www.youtube.com/watch?v=sqcLjcSloXs
        k.setIssuer(jirapp)

        # Keep it going, keep it going, keep it going full steam
        # Intergalactic Planetary
        k.start()
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

    with context:
        k = karakuri(args)

        # Initialize JIRA++
        jirapp = jirapp(args, k.mongo)
        jirapp._setLive(args.live)
        k.setJira(jirapp)

        # Initialize SFDC++
        sfdcpp = sfdcpp(args, k.mongo)
        sfdcpp._setLive(args.live)
        k.setSfdc(sfdcpp)

        # Set the Issuer. There can be only one:
        # https://www.youtube.com/watch?v=sqcLjcSloXs
        # TODO cli logic to select the Issuer
        k.setIssuer(jirapp)

        # Keep it going, keep it going, keep it going full steam
        # Intergalactic Planetary
        k.start()
sys.exit(0)
