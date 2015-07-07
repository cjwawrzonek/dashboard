import grouptestdocument
import ping
import pymongo


class Mdiag(grouptestdocument.GroupTestDocument):
    def __init__(self, groupId, jiraId=None, *args, **kwargs):
        self.mongo = kwargs['mongo']

        # Individual ping documents
        self.mdiag = {}

        try:
            self.mdiag = self.mongo.mdiags.find_one({})
        except Exception as e:
            print "ERROR!"
            print e

        from mdiag_tests import MdiagTests
        grouptestdocument.GroupTestDocument.__init__(
            self, groupId=groupId,
            mongo=self.mongo,
            src='mdiags',
            testsLibrary=MdiagTests)

    def run_all_tests(self):
        self.logger.debug("run_all_tests")
        if len(self.mdiag) == 0:
            return None
        return self.run_selected_tests(self.tests)

    def groupName(self):
        if len(self.pings) > 0:
            return self.pings.values()[0].doc['name']
        if self.group is not None:
            return self.group.get('name')
        return None

    def isTestable(self):
        return len(self.pings) > 0

    def isCsCustomer(self):
        if self.company is not None:
            return self.company.get('has_cs')
        return False
