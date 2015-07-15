import sys, os
from bson import json_util, ObjectId

class MdiagFile:
    """ This class manages mdiag uploads and processing
    """
    def __init__(self, db):
        """ Initializes Files class with a database object.
        :param filename: name of the file
        :return: None
        """
        self.db_euphonia = db.euphonia
        self.coll_mdiags = self.db_euphonia.mdiags

        self.company = None

        self.db_support = db.support
        self.coll_issues = self.db_support.issues
        self.coll_companies = self.db_support.companies

    def getTicketInfo(self, jira_key):
        if jira_key is not None:
            query = {"jira.key": jira_key}
            results = self.coll_issues.find_one(query)
            if results is not None and 'jira' in results and 'fields' in results['jira']:
                self.company = results['jira']['fields']['customfield_10030']['name']
                return {"company": self.company}
        return {}

    def getGroupInfo(self, jira_key):
        if jira_key is not None:
            company_info = self.getTicketInfo(jira_key)
            if company_info['company'] is not None:
                query = {"_id": company_info['company']}
                results = self.coll_companies.find_one(query,{"_id":1})
                if results is not None:
                    return {"gid": results['_id']}
        return {}

    def saveMdiagFile(self, content, jiraId=None):
        mdiagArray = json_util.loads(content)
        mdiagObjectId = ObjectId()
        if jiraId is not None and isinstance(mdiagArray, list):
            saveDocs = []
            for arrayItem in mdiagArray:
                arrayItem['jira_key'] = jiraId
                arrayItem['rid'] = mdiagObjectId
                arrayItem['name'] = self.getTicketInfo(jiraId).get('company')
                arrayItem['_id'] = ObjectId()
                saveDocs.append(arrayItem)
            self.coll_mdiags.insert(saveDocs)

            return True
        return False

    def processTests(self, mdiag):
        print "processed tests"

    def insert(self, mdiag, jiraId):
        print "inserting mdiag"
        print jiraId

    def upload(self, content, jiraId):
        result = self.saveMdiagFile(content, jiraId)
        return result
