import argumentparserpp
import datetime
import logging
import pymongo
import sys
import yaml


class TestFramework:
    """ I dare say this class needs a better description than this! """
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.src = self.args['src']
        # this is where we save failed test names and the corresponding failed
        # test document _ids in euphonia.groups documents
        self.failedtestsPath = 'failedtests'

        # logLevel = self.args['log_level']
        logLevel = "DEBUG"
        logging.basicConfig()
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(logLevel)

        self.mongo = pymongo.MongoClient(self.args['mongo_uri'])

        self.db = self.mongo.euphonia
        self.coll_failedtests = self.db.failedtests
        self.coll_groups = self.db.groups

        if self.src == 'mdiags':
            self.logger.info("Testing mdiags...")
            from groupmdiag import GroupMdiag as TestDocumentClass
            self.coll_src = self.db.mdiags
            self.groupIdKey = 'name'
            self.groupIdQuery = {}
        elif self.src == 'pings':
            self.logger.info("Testing pings...")
            from groupping import GroupPing as TestDocumentClass
            self.coll_src = self.db.pings
            self.groupIdKey = 'name'
            self.groupIdQuery = {}
        else:
            self.logger.exception("%s is not a supported src", self.src)
            sys.exit(1)

        self.testDocumentClass = TestDocumentClass

    def testAllGroups(self):
        self.logger.debug("testAllGroups()")
        try:
            groupIds = self.coll_src.find(self.groupIdQuery).\
                distinct(self.groupIdKey)
        except pymongo.errors.PyMongoError as e:
            raise e

        self.logger.info("%i groups", len(groupIds))
        for groupId in groupIds:
            g = self.testDocumentClass(groupId, mongo=self.mongo, src=self.src)

            if not g.isTestable():
                continue

            # CS customers only for now. I can imagine using Proactive Support
            # to sell subscriptions in the first place. If that ever happens
            # we'll give the CS customers more weight in the results.
            if not g.isCsCustomer():
                self.logger.warning("Skipping non-CS group %s", g.groupName())
                continue

            if self.args["run_tests"]:
                results = g.run_selected_tests(tests=self.args["run_tests"])
            else:
                results = g.run_all_tests()
                # could not test this group, probably there are no pings
                if results is None:
                    continue

            for testName in results:
                # If a passing test had failed previously (but has not been
                # addressed, which is why it's still listed as failed) remove
                # it from the list of failures as we'll no longer need to
                # address it ;)
                if results[testName]['payload']['pass'] is True:
                    if 'failedtests' in g.group:
                        for ft in g.group['failedtests']:
                            if ft['src'] == self.src and\
                                    ft['test'] == testName:
                                self.logger.info("Fail -> Pass! Removing %s "
                                                 "from failedtests", testName)
                                try:
                                    match = {'_id': g.groupId()}
                                    updoc = {"$pull": {self.failedtestsPath:
                                                       {'ftid': ft['ftid']}},
                                             "$inc": {'score': -1*g.
                                                      testPriorityScores[
                                                          g.tests[testName][
                                                              'priority']]}}
                                    doc = self.coll_groups.find_and_modify(
                                        query=match, update=updoc)
                                except pymongo.errors.PyMongoError as e:
                                    raise e

                                # mark the ft as resolved
                                query = {'_id': ft['ftid']}
                                updoc = {'$set':
                                         {'resolved': datetime.datetime.now()}}
                                try:
                                    self.coll_failedtests.update(query, updoc)
                                except pymongo.errors.PyMongoError as e:
                                    raise e
                    continue

                if g.tests.get(testName) is None:
                    priority = "low"
                else:
                    priority = g.tests[testName]['priority']
                score = g.testPriorityScores[priority]
                # Persist failures
                doc = {'gid': g.groupId(), 'name': g.groupName(),
                       'src': self.src, 'test': testName,
                       'ids': results[testName]['payload'].get('ids', []),
                       'nids': len(results[testName]['payload'].get('ids',
                                                                    [])),
                       'score': score}

                try:
                    ftid = self.coll_failedtests.insert(doc)
                except pymongo.errors.PyMongoError as e:
                    raise e

                match = {'_id': g.groupId()}
                updoc = {"$addToSet": {self.failedtestsPath:
                         {'src': self.src,
                          'test': testName,
                          'ftid': ftid,
                          'score': score}},
                         "$inc": {'score': score}}

                if 'failedtests' in g.group:
                    for ft in g.group['failedtests']:
                        if ft['src'] == self.src and ft['test'] == testName:
                            # it's already recorded, update with the latest
                            # failedtests _id
                            match = {'_id': g.groupId(), self.failedtestsPath:
                                     {"$elemMatch":
                                      {'src': self.src,
                                       'test': testName}}}
                            ftidPath = '%s.$.ftid' % self.failedtestsPath
                            updoc = {"$set": {ftidPath: ftid}}

                try:
                    self.coll_groups.update(match, updoc)
                except pymongo.errors.PyMongoError as e:
                    raise e


def populateTestDb(args):
    mongo = pymongo.MongoClient(args.mongo_uri)

    with open('tests.yml') as f:
        all_tests = yaml.safe_load(f)
        for test in all_tests:
            try:
                query = {"name": test["name"]}
                mongo.euphonia.tests.update(query, test, upsert=True)
            except pymongo.errors.PyMongoError as e:
                raise e

if __name__ == "__main__":
    desc = "A euphoric test framework"
    parser = argumentparserpp.CliArgumentParser(desc)
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                                    "(default=mongodb://localhost:27017)")
    parser.add_argument(
        "--run-tests",
        metavar="TESTS",
        nargs="*",
        default=None,
        help="locally run the tests for debugging, run only the selected \
            tests if this argument is present, regardless of whether they \
            are active or not")

    parser.add_argument("--populateTestDb", action='store_true',
                        help="run a script to populate the list of tests in \
                        the DB with the contents of tests.yml, to be used by \
                        the test runners")

    parser.add_argument(
        "src",
        choices=["mdiags", "mmsgroupreports", "pings"],
        nargs="?",
        help="<-- the available test frameworks, choose one")

    args = parser.parse_args()

    if args.populateTestDb:
        populateTestDb(args)
        sys.exit(0)
    t = TestFramework(args)
    t.testAllGroups()
    sys.exit(0)
