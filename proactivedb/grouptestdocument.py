import logging
import pymongo

from conversion_tools import sfProjectIdToSFProjectName


class GroupTestDocument:
    def __init__(self, groupId, mongo, src, testsLibrary=None):
        # TODO consolidate src into testsLibrary?
        # TODO remove mongo and testsLibrary from __init__?
        self.mongo = mongo
        self.src = src
        self.testsLibrary = testsLibrary
        # A support.companies document, from Clienthub
        # TODO move towards support.salesforce documents
        self.company = None
        # A euphonia.groups document, from ProactiveDB ;)
        self.group = None

        # Use existing logger if it exists
        self.logger = logging.getLogger('logger')

        res = sfProjectIdToSFProjectName(groupId, mongo)
        if not res['ok']:
            raise Exception("Failed to get group name for %s" % groupId)
        groupName = res['payload']

        # Get group doc if it exists, otherwise create it
        try:
            query = {'_id': groupId, 'name': groupName}
            updoc = {'$set': query}
            self.group = self.mongo.euphonia.groups.find_and_modify(
                query=query, update=updoc, upsert=True, new=True)
        except pymongo.errors.PyMongoError as e:
            raise e

        # Get active tests for this src type
        try:
            match = {'active': True, 'src': self.src}
            curr_tests = self.mongo.euphonia.tests.find(match)
        except pymongo.errors.PyMongoError as e:
            raise e

        self.tests = {test['name']: test for test in curr_tests}
        # TODO move out of base class
        self.testPriorityScores = {'low': 2, 'medium': 4, 'high': 8}

        # Supplement with company information if it's available
        # TODO move to a separate clienthub/sfdc library
        try:
            match = {'sf_project_id': groupId}
            curr_companies = self.mongo.support.companies.find(match)
        except pymongo.errors.PyMongoError as e:
            raise e

        if curr_companies.count() != 1:
            self.logger.warning("Unable to uniquely identify company for group"
                                "%s", groupId)
            self.company = None
        else:
            self.company = curr_companies.next()

    def groupId(self):
        return self.group['_id']

    def groupName(self):
        return self.group['name']

    # abstract
    def isTestable(self):
        pass

    # abstract
    def isCsCustomer(self):
        pass

    # abstract
    def next(self):
        pass

    # abstract
    def prev(self):
        pass

    # abstract
    def run_all_tests(self):
        pass

    def run_selected_tests(self, tests):
        res = {}
        for test in tests:
            res[test] = self.run_test(test)
        return res

    def run_test(self, test):
        self.logger.debug("run_test(%s)", test)
        if test in self.tests:
            fname = "test" + test
            try:
                f = getattr(self.testsLibrary, fname)
            except AttributeError as e:
                self.logger.exception(e)
                raise Exception(fname + " not defined")
            self.logger.debug("Testing " + test + "...")
            r = f(self)
            if r['ok'] is True:
                if r['payload']['pass'] is True:
                    self.logger.debug("Passed!")
                else:
                    self.logger.debug("Failed!")
            else:
                self.logger.debug("Test " + test + " failed to execute.")
            return r
        else:
            self.logger.exception(test + " not defined")
            raise Exception(test + " not defined")
