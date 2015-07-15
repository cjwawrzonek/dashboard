import grouptestdocument
import ping
import pymongo

from conversion_tools import mmsGroupNameToSFProjectId


class GroupPing(grouptestdocument.GroupTestDocument):
    def __init__(self, mmsGroupName, tag=None, *args, **kwargs):
        self.mmsGroupName = mmsGroupName
        self.tag = tag
        self.mongo = kwargs['mongo']

        # Individual ping documents
        self.pings = {}
        # If tag not specified get the most recent tag of the group
        if self.tag is None:
            try:
                match = {'name': mmsGroupName}
                proj = {'_id': 0, 'tag': 1}
                curr_pings = self.mongo.euphonia.pings.find(match, proj).\
                    sort("tag", -1).limit(1)
            except pymongo.errors.PyMongoError as e:
                raise e

            if curr_pings.count() > 0:
                self.tag = curr_pings[0]['tag']

        if self.tag is not None:
            try:
                # Get all pings with this tag
                match = {'tag': self.tag, 'hostInfo.deactivated': False}
                curr_pings = self.mongo.euphonia.pings.find(match)
            except pymongo.errors.PyMongoError as e:
                raise e

            for p in curr_pings:
                self.pings[p['_id']] = ping.Ping(p)

        # Get Salesforce project id
        res = mmsGroupNameToSFProjectId(mmsGroupName, self.mongo)
        if not res['ok']:
            raise Exception("Failed to determine Salesforce project id for MMS"
                            "group %s" % mmsGroupName)
        gid = res['payload']

        from groupping_tests import GroupPingTests
        grouptestdocument.GroupTestDocument.__init__(
            self, groupId=gid,
            mongo=self.mongo,
            src='pings',
            testsLibrary=GroupPingTests)

    def run_all_tests(self):
        self.logger.debug("run_all_tests")
        if len(self.pings) == 0:
            return None
        return self.run_selected_tests(self.tests)

    def isTestable(self):
        return len(self.pings) > 0

    def isCsCustomer(self):
        if self.company is not None:
            return self.company.get('has_cs')
        return False

    def forEachHost(self, test, *args, **kwargs):
        ok = True
        res = True
        ids = []
        for pid in self.pings:
            testRes = test(self.pings[pid], *args, **kwargs)
            if testRes is None:
                ok = False
                # self.logger.warning('Test returned bad document format')
            elif not testRes:
                res = False
                ids.append(pid)
        return {'ok': ok, 'payload': {'pass': res, 'ids': ids}}

    def forEachPrimary(self, test, *args, **kwargs):
        ok = True
        res = True
        ids = []
        for pid in self.pings:
            if self.pings[pid].isPrimary():
                testRes = test(self.pings[pid], *args, **kwargs)
                if testRes is None:
                    ok = False
                    # self.logger.warning('Test returned bad document format')
                elif not testRes:
                    res = False
                    ids.append(pid)
        return {'ok': ok, 'payload': {'pass': res, 'ids': ids}}

    def next(self):
        """ Return the GroupPing after this one """
        try:
            match = {'name': self.mmsGroupName, 'tag': {"$gt": self.tag}}
            proj = {'tag': 1, '_id': 0}
            curr_pings = self.mongo.euphonia.pings.find(match, proj).\
                sort("tag", -1).limit(1)
        except pymongo.errors.PyMongoError as e:
            raise e

        if curr_pings.count() > 0:
            tag = curr_pings[0]['tag']
            return GroupPing(self.mmsGroupName, tag, mongo=self.mongo,
                             src=self.src)
        else:
            return None

    def prev(self):
        """ Return the GroupPing before this one """
        try:
            match = {'name': self.mmsGroupName, 'tag': {"$lt": self.tag}}
            proj = {'tag': 1, '_id': 0}
            curr_pings = self.mongo.euphonia.pings.find(match, proj).\
                sort("tag", 1).limit(1)
        except pymongo.errors.PyMongoError as e:
            raise e

        if curr_pings.count() > 0:
            tag = curr_pings[0]['tag']

            # make sure this tag contains useful pings!
            try:
                match = {'tag': tag, 'hostInfo.deactivated': False}
                curr_pings = self.mongo.euphonia.pings.find(match)
            except pymongo.errors.PyMongoError as e:
                raise e

            if curr_pings.count() > 0:
                return GroupPing(self.mmsGroupName, tag, mongo=self.mongo,
                                 src=self.src)
        return None
