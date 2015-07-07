import sys, os
from bson import json_util

class Mdiag:
    """ This class manages mdiag uploads and processing
    """
    def __init__(self, db):
        """ Initializes Files class with a database object.
        :param filename: name of the file
        :return: None
        """
        self.db_euphonia = db.euphonia
        self.coll_mdiag = self.db_euphonia.mdiag

        self.mdiag = []

        self.db_support = db.support
        self.coll_issues = self.db_support.issues

    # def process_group_report(self):
    #     sys.argv = ['importGroupReports.py', self.filename]
    #     print os.path.dirname(__file__)
    #     os.chdir(os.path.dirname(__file__))
    #     os.chdir('..')
    #     print os.getcwd()
    #     execfile('importGroupReports.py')

    def getTicketInfo(self, jira_key):
        if jira_key is not None:
            query = {"jira.key": jira_key}
            results = self.coll_issues.find_one(query)
            if results is not None and 'jira' in results and 'fields' in results['jira']:
                return {"company": results['jira']['fields']['customfield_10030']['name']}
        return {}

    def processMdiagFile(self, content, jiraId=None):
        array = json_util.loads(content)
        finalDoc = {}
        if jiraId is not None:
            finalDoc['jira_key'] = jiraId
        finalDoc['results'] = array
        return finalDoc

    def processTests(self, mdiag):
        print "processed tests"

    def insert(self, mdiag, jiraId):
        print "inserting mdiag"
        print jiraId

    def upload(self, content, jiraId):
        mdiag_content = self.processMdiagFile(content)
        self.mdiag.append(mdiag_content)