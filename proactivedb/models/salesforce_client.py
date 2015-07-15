import pyforce


class Salesforce:
    """ This class manages the Salesforce connection and queries
    """

    def __init__(self, args):
        """ Initializes Tests class with a database object.
        :return: None
        """
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        self.connection = pyforce.PythonClient(self.args['sf_server'])
        # TODO try/except
        self.connection.login(self.args['sf_username'], self.args['sf_password'])

    def get_contacts(self):
        """ INCOMPLETE FUNCTION
        :return: Boolean
        """
        return self.connection.isConnected()

    def get_sf_project_onboard_status(self):
        """ INCOMPLETE FUNCTION
        :return: Boolean
        """
        soql = "SELECT Account_Name_text__c,Account__c,Clienthub_ID__c,Id,Name FROM Project__c ORDER BY Name"
        results = self.connection.query(soql)
        while not results.done:
            for result in results:
                print result['Name']
            results = self.connection.queryMore(self.connection.queryLocator)
        return True
