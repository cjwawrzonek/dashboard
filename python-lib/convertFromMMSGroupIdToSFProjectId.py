import copy
import logging
import pymongo

from conversion_tools import mmsGroupNameToSFProjectId
from conversion_tools import sfProjectIdToSFProjectName

logging.basicConfig(format='%(asctime)s - %(module)s - %(levelname)s - '
                           '%(message)s')
logger = logging.getLogger("logger")
logger.setLevel("DEBUG")

mongo = pymongo.MongoClient()

# Convert groups documents to the new schema. They will be placed in a new
# collection which will need to be renamed manually. groups for which we were
# not able to identify a Salesforce project id will be moved to lostgroups
coll_groups = mongo.euphonia.groups
coll_newgroups = mongo.euphonia.newgroups
coll_lostgroups = mongo.euphonia.lostgroups
try:
    curr = coll_groups.find()
except pymongo.errors.PyMongoError as e:
    raise e
for doc in curr:
    mmsGroupName = doc.get('name')
    res = mmsGroupNameToSFProjectId(mmsGroupName, mongo)
    if not res['ok']:
        logger.warning(res['payload'])
        coll_lostgroups.insert(doc)
    else:
        logger.info("%s -> %s", mmsGroupName, res['payload'])
        newdoc = {'_id': res['payload']}

        res = sfProjectIdToSFProjectName(res['payload'], mongo)
        if not res['ok']:
            logger.warning(res['payload'])
            continue
        newdoc['name'] = res['payload']

        if 'failedTests' in doc:
            newdoc['failedtests'] = copy.deepcopy(doc['failedTests'])
            del doc['failedTests']
        if 'score' in doc:
            newdoc['score'] = copy.deepcopy(doc['score'])
            del doc['score']
        # the rest is MMS
        doc['id'] = copy.deepcopy(doc['_id'])
        del doc['_id']

        newdoc['mms'] = [doc]
        try:
            coll_newgroups.insert(newdoc)
        except pymongo.errors.DuplicateKeyError as e:
            # The corresponding SF project exists, so we add the MMS group,
            # the failedtests and the score to the existing document
            match = {'_id': newdoc['_id']}
            updoc = {"$push": {'mms': {"$each": newdoc['mms']}}}
            if 'failedtests' in newdoc:
                updoc["$push"]['failedtests'] = {"$each": newdoc['failedtests']}
            if 'score' in newdoc:
                updoc["$inc"] = {'score': newdoc['score']}
            try:
                coll_newgroups.update(match, updoc)
            except pymongo.errors.PyMongoError as e:
                raise e
        except pymongo.errors.PyMongoError as e:
            raise e

# Convert failedtests documents to the new schema. They will be placed in a new
# collection which will need to be renamed manually. failedtests for which we
# were not able to identify a Salesforce project id will be moved to
# lostfailedtests
coll_failedtests = mongo.euphonia.failedtests
coll_newfailedtests = mongo.euphonia.newfailedtests
coll_lostfailedtests = mongo.euphonia.lostfailedtests
try:
    curr = coll_failedtests.find()
except pymongo.errors.PyMongoError as e:
    raise e
for doc in curr:
    mmsGroupName = doc.get('name')
    res = mmsGroupNameToSFProjectId(mmsGroupName, mongo)
    if not res['ok']:
        logger.warning(res['payload'])
        coll_lostfailedtests.insert(doc)
    else:
        logger.info("%s -> %s", mmsGroupName, res['payload'])
        doc['gid'] = res['payload']
        res = sfProjectIdToSFProjectName(res['payload'], mongo)
        if not res['ok']:
            logger.warning(res['payload'])
            continue
        doc['name'] = res['payload']
        coll_newfailedtests.insert(doc)
