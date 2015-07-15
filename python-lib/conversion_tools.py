import logging
import pymongo
import re


def jiraGroupToSFProjectId(group, mongo):
    """ Return the Salesforce project id associated to the given JIRA group """
    logger = logging.getLogger("logger")
    logger.debug("jiraGroupToSFProjectId(%s)", group)
    # TODO move to support.salesforce
    coll_companies = mongo.support.companies

    try:
        match = {'_id': group}
        proj = {'_id': 0, 'sf_project_id': 1}
        doc = coll_companies.find_one(match, proj)
    except pymongo.errors.PyMongoError as e:
        return {'ok': False, 'payload': e}

    if doc is None:
        return {'ok': False,
                'payload': 'Unable to identify SF project id for JIRA group %s'
                           '' % group}
    return {'ok': True, 'payload': doc['sf_project_id']}


def mmsGroupNameToSFProjectId(name, mongo):
    """ Return the Salesforce project id associated to the given MMS group name
    """
    logger = logging.getLogger("logger")
    logger.debug("mmsGroupNameToSFProjectId(%s)", name)
    coll_companies = mongo.support.companies
    coll_salesforce = mongo.support.salesforce

    # NOTE I am using regex here because I do not trust the data to be clean.
    # If the data proves trustworthy in the future, move to an exact match
    regex = re.compile('^%s$' % name, re.IGNORECASE)

    try:
        match = {"$or": [{'projects.MMS_Group_Name__c': regex},
                         {'projects.Support_Jira_Groups__c': regex}]}
        cursor = coll_salesforce.find(match)
    except pymongo.errors.PyMongoError as e:
        return {'ok': False, 'payload': e}

    # If there are no matches, try to identify a matching Clienthub document
    if cursor.count() == 0:
        logger.debug("Not found in Salesforce, trying Clienthub")
        try:
            match = {"$or": [{'mms_groups': regex}, {'jira_groups': regex}]}
            cursor = coll_companies.find(match)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}

        # If there are still no matches, then we have failed completely and cry
        if cursor.count() == 0:
            logger.debug("Not found in Clienthub")
            return {'ok': False,
                    'payload': 'Unable to identify business object for MMS '
                               'group %s' % name}
        elif cursor.count() > 1:
            logger.debug(">1 match in Clienthub, data needs cleaning")
            return {'ok': False,
                    'payload': 'Unable to identify business object for MMS '
                               'group %s' % name}
        else:
            logger.debug("Found in Clienthub")
            doc = cursor.next()
            return {'ok': True, 'payload': doc.get('sf_project_id')}
    elif cursor.count() > 1:
        logger.debug(">1 match in Salesforce, data needs cleaning")
        return {'ok': False,
                'payload': 'Unable to identify business object for MMS group '
                           '%s' % name}
    else:
        logger.debug("Found in Salesforce")
        res = None
        doc = cursor.next()
        # To which project did we match?
        projects = doc.get('projects')
        if projects is not None:
            for proj in projects:
                if regex.match(proj.get('MMS_Group_Name__c')) is not None:
                    res = proj.get('Id')
                    break
                if regex.match(proj.get('Support_Jira_Groups__c')) is not None:
                    res = proj.get('Id')
                    break
        # This should never happen, but just in case...
        if res is None:
            logger.debug("How did we get here!?")
            return {'ok': False,
                    'payload': 'Unable to identify business object for MMS '
                               'group %s' % name}
        return {'ok': True, 'payload': res}


def sfProjectIdToSFProjectName(sfid, mongo):
    """ Return the Salesforce project name for the given Salesforce project id
    """
    logger = logging.getLogger("logger")
    logger.debug("sfProjectIdToSFProjectName(%s)", sfid)
    coll_salesforce = mongo.support.salesforce

    try:
        match = {'projects.Id': sfid}
        proj = {'_id': 0, 'projects.Id': 1, 'projects.Name': 1}
        cursor = coll_salesforce.find(match, proj)
    except pymongo.errors.PyMongoError as e:
        return {'ok': False, 'payload': e}

    # There can be only one!
    if cursor.count() != 1:
        return {'ok': False,
                'payload': 'Unable to uniquely identify SF project %s' % sfid}
    res = None
    doc = cursor.next()
    # To which project did we match?
    projects = doc.get('projects')
    if projects is not None:
        for proj in projects:
            projId = proj.get('Id')
            if projId is not None and projId == sfid:
                res = proj.get('Name')
                break
    # This should never happen, but just in case...
    if res is None:
        logger.debug("How did we get here!?")
        return {'ok': False,
                'payload': 'Unable to uniquely identify SF Project %s' % sfid}
    return {'ok': True, 'payload': res}
