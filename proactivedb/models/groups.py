import pymongo


class Groups:
    """ This class manages the MMS group content.
    """

    def __init__(self, mongo):
        """ Initializes Groups class with a database object.
        :param database: MongoDB client object
        :return: None
        """
        self.db_euphonia = mongo.euphonia
        self.db_support = mongo.support
        self.coll_groups = self.db_euphonia.groups
        self.coll_pings = self.db_euphonia.pings
        self.coll_failedtests = self.db_euphonia.failedtests

    def getGroupSummary(self, gid):
        """ Retrieve that needed to render the group page
        :param gid: Group ID
        :return: Dict containing everything there is to know
        """
        # High-level information
        query = {'_id': gid}
        try:
            res = self.coll_groups.find_one(query)
        except pymongo.errors.PyMongoError as e:
            raise e

        if res is not None:
            group_summary = res
        else:
            # TODO raise exception?
            group_summary = {'gid': gid}

        # Failed tests
        # This is the list of currently failed tests
        failedtests = group_summary.get('failedtests', [])
        failedtestsDict = {ft['ftid']: ft for ft in failedtests}

        # Have we created tickets for these failed tests before?
        # Return the most recent one if so
        # TODO remove this loop!
        # TODO consolidate test and src
        # TODO are we better off just querying all ticketed cases?
        for i in range(0, len(failedtests)):
            ft = failedtests[i]
            query = {'gid': gid,
                     'test': ft['test'],
                     'src': ft['src'],
                     '_id': {"$lt": ft['ftid']},
                     'ticket': {"$exists": True}}
            sort = [("_id", -1)]
            try:
                res = self.coll_failedtests.find(query).sort(sort).limit(1)
            except pymongo.errors.PyMongoError as e:
                raise e

            if res is not None:
                print("Found a previous ticket for this test!")
                test = next(res, None)
                if test is not None:
                    failedtests[i]['ticket'] = test['ticket']

        # Fetch these failed tests as we'll need their src documents
        query = {'_id': {"$in": [ft['ftid'] for ft in failedtests]}}
        try:
            res = self.coll_failedtests.find(query)
        except pymongo.errors.PyMongoError as e:
            raise e

        failedtests = []
        testDocuments = {}

        if res is not None:
            for ft in res:
                if ft['src'] not in testDocuments:
                    testDocuments[ft['src']] = []
                testDocuments[ft['src']].extend(ft['ids'])
                for key in ft.keys():
                    failedtestsDict[ft['_id']][key] = ft[key]
                failedtests.append(failedtestsDict[ft['_id']])
        else:
            # TODO raise exception?
            pass

        # Get all past failed tests that are now resolved
        query = {'gid': gid, 'resolved': {"$exists": True}}
        resolvedTests = []
        try:
            res = self.coll_failedtests.find(query)
        except pymongo.errors.PyMongoError as e:
            raise e

        for ft in res:
            resolvedTests.append(ft)
            if ft['src'] in testDocuments:
                testDocuments[ft['src']].extend(ft['ids'])
            else:
                testDocuments[ft['src']] = ft['ids']

        group_summary['failedtests'] = failedtests
        group_summary['resolvedTests'] = resolvedTests

        # Fetch test documents
        ids = {}
        for key in testDocuments:
            query = {"_id": {"$in": testDocuments[key]}}
            try:
                res = self.db_euphonia[key].find(query)
            except pymongo.errors.PyMongoError as e:
                raise e

            for r in res:
                if 'doc' in r:
                    doc = r['doc']
                    if 'configCollections' in doc:
                        del doc['configCollections']
                    if 'configLockpings' in doc:
                        del doc['configLockpings']
                    if 'locks' in doc:
                        del doc['locks']
                    if 'serverStatus' in doc:
                        del doc['serverStatus']
                    if 'oplog' in doc:
                        del doc['oplog']
                    if 'connPoolStats' in doc:
                        del doc['connPoolStats']
                ids[r['_id'].__str__()] = r

        group_summary['ids'] = ids

        # Supplement with Clienthub info
        # TODO move this to a separate library

        try:
            match = {'sf_project_id': gid}
            curr_companies = self.db_support.companies.find(match)
        except pymongo.errors.PyMongoError as e:
            raise e

        if curr_companies.count() != 1:
            self.logger.warning("Unable to identify business object for group "
                                "%s", gid)
            group_summary['company'] = None
        else:
            group_summary['company'] = curr_companies.next()
        return group_summary

    def search(self, query):
        """ Performs an auto-complete lookup on Group Names for the search box
        :param query: Partial group name to match
        :return: Array of group summary docs
        """
        qregex = ".*%s.*" % query
        query = {"name": {"$regex": qregex, "$options": "i"}}
        project = {"name": 1, "gid": 1, "_id": 0}
        results = self.coll_pings.find(query, project)\
                      .sort("name", 1)\
                      .limit(10)
        groups = []
        group = next(results, None)
        while group is not None:
            groups.append(group)
            group = next(results, None)
        return groups
