import grouptestdocument
import logging
import mdiag
import pymongo
import re

from conversion_tools import jiraGroupToSFProjectId


# TODO move this elsewhere
def _stringToIntIfPossible(s):
    # if (typeof s == "object" && "map" in s) {
    #     return s.map(_stringToIntIfPossible);
    # } else {
    if isinstance(s, str) or isinstance(s, unicode):
        if re.match('^[0-9]+$', s) is not None:
            return int(s)
    return s


class GroupMdiag(grouptestdocument.GroupTestDocument):
    def __init__(self, jiraGroup, run=None, *args, **kwargs):
        self.logger = logging.getLogger("logger")
        self.jiraGroup = jiraGroup
        self.run = run
        self.mongo = kwargs['mongo']

        # If run not specified get the most recent run of the group
        if self.run is None:
            try:
                match = {'name': jiraGroup}
                proj = {'_id': 0, 'run': 1}
                curr_mdiags = self.mongo.euphonia.mdiags.find(match, proj).\
                    sort("run", -1).limit(1)
            except pymongo.errors.PyMongoError as e:
                raise e

            if curr_mdiags.count() > 0:
                self.run = curr_mdiags[0]['run']

        # Get Salesforce project id
        res = jiraGroupToSFProjectId(jiraGroup, self.mongo)
        if not res['ok']:
            raise Exception("Failed to determine Salesforce project id for"
                            "JIRA group %s" % jiraGroup)
        gid = res['payload']

        from groupmdiag_tests import GroupMdiagTests
        grouptestdocument.GroupTestDocument.__init__(
            self, groupId=gid,
            mongo=self.mongo,
            src='mdiags',
            testsLibrary=GroupMdiagTests)

    def getc(self, query, proj=None):
        query['run'] = self.run
        try:
            if proj is not None:
                return self.mongo.euphonia.mdiags.find(query, proj)
            return self.mongo.euphonia.mdiags.find(query)
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
        return None

    def getMongoProcesses(self):
        pidIdMap = {}
        match = {'section': {"$regex": '^proc/[0-9]+$'},
                 'subsection': 'cmdline', 'rc': 0, 'output': {"$exists": 1}}
        c = self.getc(match)
        for doc in c:
            md = mdiag.Mdiag(doc)
            name = md.getProcessName()
            if name is not None:
                pid = md.getProcessPid()
                if pid is not None:
                    pidIdMap[pid] = {'id': md.doc['_id'], 'name': name}
        return pidIdMap

    def getProcPidLimits(self):
        pidLimits = {}
        # TODO move names out of this function
        names = {
            "Max cpu time": "cpu",
            "Max file size": "fsize",
            "Max data size": "data",
            "Max stack size": "stack",
            "Max core file size": "core",
            "Max resident set": "rss",
            "Max processes": "nproc",
            "Max open files": "nofile",
            "Max locked memory": "memlock",
            "Max address space": "as",
            "Max file locks": "locks",
            "Max pending signals": "sigpending",
            "Max msgqueue size": "msgqueue",
            "Max nice priority": "nice",
            "Max realtime priority": "rtprio",
            "Max realtime timeout": "rttime"
        }
        c = self.getc({'filename': {"$regex": "^/proc/[0-9]+/limits$"},
                       'exists': True, 'content': {"$exists": True}})
        for doc in c:
            md = mdiag.Mdiag(doc)
            pid = md.getProcessPid()
            if pid is None:
                continue
            limits = {}
            # Skip first line
            for i in range(1, len(md.doc['content'])):
                line = md.doc['content'][i]
                desc = None
                for key in names:
                    if line.startswith(key):
                        desc = key
                        break
                if desc is not None:
                    name = names[desc]
                    words = line[len(desc):].strip().replace(' +', " ").\
                        split(" ")
                    if len(words) >= 2:
                        limits[name] = {'desc': desc,
                                        'soft': _stringToIntIfPossible(
                                            words[0]),
                                        'hard': _stringToIntIfPossible(
                                            words[1])}
                        if len(words) >= 3:
                            limits[name]['units'] = words[2]
            pidLimits[pid] = limits
        return pidLimits

    def getRun(self):
        return self.run

    def run_all_tests(self):
        self.logger.debug("run_all_tests")
        if self.isTestable():
            self.logger.debug(self.tests)
            return self.run_selected_tests(self.tests)
        return None

    def groupName(self):
        return self.name

    def isTestable(self):
        return self.run is not None

    def isCsCustomer(self):
        if self.company is not None:
            return self.company.get('has_cs')
        return False

    def getTestDefinitions(self):
        res = {}
        if self.tests is not None:
            res.update(self.tests)
            return res
        return None
