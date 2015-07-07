#!/usr/bin/env python
import argumentparserpp
import logging
import pyforce
import pymongo
import math
import sys
import time

from datetime import date


class sfdcpp():
    def __init__(self, args, mongo=None):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        logging.basicConfig(format='%(asctime)s - %(module)s - %(levelname)s -'
                                   ' %(message)s')
        self.logger = logging.getLogger("logger")
        self.logger.setLevel(self.args['log_level'])
        fh = logging.FileHandler(self.args['log'])
        self.logger.addHandler(fh)

        self.logger.info("Initializing SFDC++")
        self.logger.debug(self.args)

        if mongo is None:
            try:
                self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
            except pymongo.errors.PyMongoError as e:
                self.logger.exception(e)
                raise e
        else:
            self.mongo = mongo

        # Initialize dbs and collections
        self.db_support = self.mongo.support

        self.login()

    def login(self):
        try:
            self.sfdc = pyforce.PythonClient()
            self.sfdc.login(self.args['sfdc_username'],
                            self.args['sfdc_password'])
        except pyforce.SoapFaultError as e:
            self.logger.exception(e)
            raise e

    def querySFDC(self, query):
        self.logger.debug("querySFDC(%s)", query)
        first = True
        done = False
        result = []
        # cursor (queryLocator) for queryMore
        cursor = None
        batchIt = 1
        while done is False:
            # wait a spell so as not to piss off Arnt [too much]
            time.sleep(float(self.args.get('timeout', 0)))
            if first is True:
                try:
                    res = self.sfdc.query(query)
                except pyforce.SoapFaultError as e:
                    self.logger.exception(e)
                    return {'ok': False, 'payload': e}
                first = False
                if res.done is False:
                    batchSize = len(res)
                    nBatches = int(math.ceil(float(res.size)/float(batchSize)))
                    self.logger.info("Fetched batch 1 of %i", nBatches)
            else:
                if cursor is None:
                    return {'ok': False,
                            'payload': 'Unable to queryMore, invalid cursor'}
                self.logger.info("Fetching batch %i of %i", batchIt, nBatches)
                try:
                    res = self.sfdc.queryMore(cursor)
                except pyforce.SoapFaultError as e:
                    self.logger.exception(e)
                    return {'ok': False, 'payload': e}
            result.extend(res)
            done = res.done
            batchIt += 1
            cursor = res.queryLocator
        return {'ok': True, 'payload': result}

    # TODO move this to a common lib?
    def convertFieldIllegals(self, doc):
        keys = doc.keys()
        for key in keys:
            if key.find('.') > -1:
                newKey = key.replace('.', '\\p')
                doc[newKey] = doc.pop(key)
                key = newKey

            if key.startswith('$'):
                newKey = "\\$%s" % key[1:]
                doc[newKey] = doc.pop(key)
                key = newKey

            # coolio! now recursively scan values for keys
            val = doc[key]
            if isinstance(val, dict):
                doc[key] = self.convertFieldIllegals(val)
            elif isinstance(val, list):
                newVal = []
                for item in val:
                    if isinstance(item, dict):
                        newVal.append(self.convertFieldIllegals(item))
                    else:
                        newVal.append(item)
                doc[key] = newVal
            elif isinstance(val, date):
                doc[key] = str(val.isoformat())
        return doc

    def getAccounts(self):
        self.logger.debug("getAccounts()")
        query = "SELECT Id FROM Account"
        return self.querySFDC(query)

    # First_MMS_Date__c, Fiscal_Year_End__c, Number_of_Emails_and_Email_Domains__c, Rankings_DandB_Import__c,Site
    def getAccount(self, accountId):
        self.logger.debug("getAccount(%s)", accountId)
        query = """SELECT Account_City__c,Account_Country__c,Account_count__c,
                   Account_Coverage__c,Account_State__c,AnnualRevenue,Annual_Revenue_Roll_up__c,
                   Balance__c,Certified_Training_Partner__c,Clienthub_Id__c,Customer_Since__c,
                   Customer_Status__c,Description,Doing_Business_As__c,
                   First_Services_Date__c,First_Subscription_Date__c,Fiscal_Year_End_Month__c,
                   Has_Support_Product__c,Hosting_Partner__c,
                   How_are_they_using_MongoDB__c,Id,ID_18__c,Industry,IsCustomerPortal,IsDeleted,
                   IsPartner,LastActivityDate,LastModifiedById,LastModifiedDate,
                   Last_Subscription_Date__c,Marketing_Terms_Description__c,Marketing_Term_std__c,
                   MasterRecordId,MongoDB_Stage__c,Mongo_Territory__c,Name,NumberOfEmployees,
                   Number_of_Open_Opportunities__c,
                   Number_of_Opportunities__c,Number_of_Q1_Open_Opportunities__c,Ownership,
                   Partner_Program_Level__c,Partner_Registration_Accepted__c,Partner_Since__c,
                   Partner_Technical_Certification_Expiry__c,Partner_Tier__c,Partner_Top_Customers__c,
                   Partner_Type__c,Partner_Verticals__c,Primary_Support_Contact_Email__c,
                   Primary_Support_Contact__c,
                   Reseller_Partner_Contract_Expiry__c,Reseller_Training__c,Reseller__c,
                   Secondary_Support_Contact__c,SI__c,Solution__c,Sub_Industry__c,
                   Support_Provider__c,Suspended_Reason__c,Suspended__c,SystemModstamp,Total_Won_Deals__c,
                   Training_Partner_Expiry_Date__c,Type,Website,Why_MongoDB__c
                   FROM Account WHERE Id = '%s'""" % accountId
        return self.querySFDC(query)

    def getAccountOpportunities(self, accountId):
        self.logger.debug("getAccountOpportunities(%s)", accountId)
        query = """SELECT Id FROM Opportunity WHERE AccountId = '%s'""" % accountId
        return self.querySFDC(query)

    def getAccountOpportunity(self, opportunityId):
        self.logger.debug("getAccountOpportunity(%s)", opportunityId)
        query = """SELECT AccountId,ACV_Bookings_Net_New__c,ACV_Bookings_Renewal__c,ACV_Bookings__c,
                   ACV_Net_New__c,ACV_Renewal__c,ACV__c,Amount,CloseDate,Id,IsClosed,IsWon,LastActivityDate,
                   LastModifiedDate,Name,NS_Project_ID__c,Number_of_Backup_Subscription_Lines__c,
                   Number_of_Consulting_Lines__c,Number_of_MMS_Subscription_Lines__c,
                   Number_of_Support_Lines__c,Number_of_Training_Lines__c,Pricebook2Id,Project_Name__c,
                   Renewal_Year__c,StageName,Type
                   FROM Opportunity WHERE Id = '%s'""" % opportunityId
        return self.querySFDC(query)

    # Account_Region_Intacct_Id__c, ACV_Include__c, Delivered_Amt__c, Discount, Finance_Bucket__c, Intacct_Location_ID__c, Make_whole_for_Commissions__c, Make_whole_for_Finance__c, Opp_Owner_Intacct_Id__c, Product_Sub_Family__c, Renewable__c, ServiceEndDate__c, Subtotal, Suppress_Commissions__c, Term_Days_Default__c
    def getAccountOpportunityProducts(self, opportunityId):
        self.logger.debug("getAccountOpportunityProducts(%s)", opportunityId)
        query = """SELECT Active_Subscriptions__c,ACV_Line__c,
                   Commission_Bucket__c,CreatedById,CreatedDate,CurrencyIsoCode,
                   Delivered_Days__c,Delivered_Hours__c,Delivered_Qty_formula__c,Delivered__c,
                   Description,Discount_Perc__c,Expired_Amt__c,Expired_Days__c,Expired_Hours__c,
                   Expired_Qty_formula__c,Expired_Qty__c,Id,IsDeleted,
                   LastModifiedById,LastModifiedDate,ListPrice,List_Price_Prorated__c,
                   OA_Task_Closed__c,OA_Task_ID__c,
                   OpportunityId,Override_Dates__c,PricebookEntryId,
                   product_end_date__c,Product_Family__c,Prod_Code__c,
                   prod_start_date__c,Quantity,Remaining_Days__c,Remaining_Hours__c,Remaining_Qty__c,
                   ServiceDate,Service_hours_Unit__c,Sold_Days__c,Sold_Hours__c,
                   SortOrder,Suppress_Bookings__c,SystemModstamp,
                   Term_Days__c,Term__c,TotalPrice,Total_Price_Carved_out__c,
                   Total_Price_Finance__c,UnitPrice,X18_digit_ID_OLI__c
                   FROM OpportunityLineItem WHERE OpportunityId = '%s'""" % opportunityId
        return self.querySFDC(query)

    # Initial_Response_Entitlement__c, Support_Level__c,
    def getAccountProjects(self, accountId):
        self.logger.debug("getAccountProjects(%s)", accountId)
        query = """SELECT Account_Name_text__c,Account__c,Additional_Notes_Backup__c,
                   Additional_Notes_Data_Size__c,Additional_Notes_general__c,Additional_Notes_Languages__c,
                   Additional_Notes_MongoDB_Setup__c,Additional_Notes_Storage__c,Backup_Strategy__c,
                   Business_Contact__c,Business_Goals_Detail__c,Business_Goals__c,Check_in_Date__c,
                   Clienthub_ID__c,Cloud_Provider__c,Cores__c,CreatedById,CreatedDate,CurrencyIsoCode,
                   Data_Directory_On_Dedicated_Drive__c,Date_Time_submitted__c,Delayed_Slaves__c,Department__c,
                   Description__c,Disks__c,Disk_Type__c,Documents_6months__c,Documents_12Months__c,
                   Documents_Now__c,EBS_Volumes__c,EC2_Disk_Type__c,EC2_Instance_Type__c,Filesystem__c,
                   Fit_Rating__c,Follow_up_Date__c,Go_Live_Date__c,How_do_you_manage_backups__c,Id,
                   IsDeleted,Java_ORM__c,Journal_Directory_on_Dedicated_Drive__c,
                   Languages_Used__c,LastActivityDate,LastModifiedById,LastModifiedDate,
                   Local_Time_Zone_Business_Hours__c,Log_Path_On_Dedicated_Drive__c,
                   MMS_Group_Name__c,MongoDB_Hosting__c,MongoDB_Version__c,Multiple_MongoDB_Version__c,Name,
                   node_js_ORM__c,Number_Arbiters__c,Number_Config_Servers__c,Number_Hidden__c,Number_Replicas__c,
                   Number_Routers__c,Number_Shards__c,Offboarded_Date__c,Onboarded_Date__c,Onboarding_Form__c,
                   Onboarding_Status__c,Onboard_Form_completed__c,Onboard_Form_Open_Closed__c,One_Time_Key__c,
                   Open_for_TSE__c,Open_Questionnaire__c,OS_Version__c,OS__c,OtherSAN_NAS__c,
                   Other_Cloud_Provider__c,Other_Filesystem__c,Other_Languages_and_Drivers__c,
                   Other_MongoDB_Hosting__c,Other_OS__c,Other_Virtualization__c,PHP_ORM__c,Primary_Jira_Group__c,
                   Primary_Solution_Architect__c,Primary_Support_Contact__c,Project_Completion__c,
                   Project_Count__c,Project_Name_submitted__c,Project_Summary__c,Provisioned_IOPS__c,
                   Python_ORM__c,Questionnaire_completed__c,Questionnaire_URL_TSE__c,Questionnaire_URL__c,
                   RAID__c,RAM_GB__c,Reads_Second_6months__c,Reads_Second_12months__c,Reads_Second_Now__c,
                   RPM__c,Ruby_ORM__c,SAN_NAS_Vendor__c,SA_Engaged__c,Scala_ORM__c,Secondary_Support_Contact__c,
                   Servers_Virtualization__c,Server_Type__c,SLA_Blocker_minutes__c,SLA_Critical_minutes__c,
                   SLA_Major_minutes__c,SLA_Minor_minutes__c,Storage_Architecture__c,Submitted_by_Email__c,
                   Submitted_by_Name__c,Support_Expiration_Date__c,Support_Jira_Groups__c,
                   SystemModstamp,Total_Data_Size_6months_GB__c,Total_Data_Size_12months_GB__c,
                   Total_Data_Size_GB__c,Total__c,Use_Case_Type__c,Use_Case__c,Using_MMS__c,Using_PIOPS__c,
                   Using_Sharding__c,View_In_Clienthub__c,Volume_Setup_On_Dedicated_Drive__c,
                   Writes_Second_6months__c,Writes_Second_12months__c,Writes_Second__c
                   FROM Project__c WHERE Account__c = '%s'""" % accountId
        return self.querySFDC(query)

    def getListOfAccountIds(self):
        self.logger.debug("getListOfAccountIds()")
        res = self.getAccounts()
        if not res['ok']:
            return res
        accounts = res['payload']
        ids = [a['Id'] for a in accounts]
        return {'ok': True, 'payload': ids}

    def healthcheck(self, **kwargs):
        """ Perform sanity checks """
        isOk = True
        messages = []
        # Are we locked out of MongoDB?
        if self.mongo.is_locked is True:
            isOk = False
            messages.append("sfdcpp: mongo is locked, no write access")
        # Can we access Salesforce?
        try:
            self.sfdc.getServerTimestamp()
        except pyforce.SoapFaultError as e:
            self.logger.exception(e)
            isOk = False
            messages.append("sfdcpp: unable to get SF server timestamp")
        # Can we read from the collections we use?
        try:
            self.db_support.salesforce.find_one({"_id": 1})
            self.db_support.companies.find_one({"_id": 1})
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            isOk = False
            messages.append("sfdcpp: unable to read from support db: %s" % e)
        return {'ok': isOk, 'payload': messages}

    def run(self):
        self.logger.debug("run()")
        if self.args['query_who'] == 'all':
            # all groups
            res = self.getListOfAccountIds()
            if not res['ok']:
                self.logger.warning(res['payload'])
                return res
            self.args['sid'] = res['payload']
        self.logger.info("Querying %s groups", len(self.args['sid']))
        i = 0
        for sid in self.args['sid']:
            i += 1
            if (i + 1) % 10 == 0:
                self.logger.info("... %i (%.2f %%)", i+1,
                                 float(i+1)*100./len(self.args['sid']))
            if self.args['query_type'] == "all":
                res = self.saveAccount(sid, details=True)
                if not res['ok']:
                    self.logger.warning(res['payload'])
            elif self.args['query_type'] == "accountOnly":
                res = self.saveAccount(sid, details=False)
                if not res['ok']:
                    self.logger.warning(res['payload'])
            else:
                self.logger.warning("Unknown query_type specified")
                sys.exit(3)

    def saveAccount(self, accountId, details=True):
        self.logger.debug("saveAccount(%s,%s)", accountId, details)
        res = self.getAccount(accountId)
        if not res['ok']:
            self.logger.warning(res['payload'])
            return res
        if len(res['payload']) == 0:
            self.logger.warning("Account %s not found", accountId)
            return res
        doc = res['payload'][0]
        if details is True:
            res = self.getAccountOpportunities(accountId)
            if not res['ok']:
                self.logger.warning(res['payload'])
                return res
            opportunities = res['payload']

            oppArray = []
            for opportunity in opportunities:
                oppId = opportunity['Id']
                res = self.getAccountOpportunityProducts(oppId)
                if not res['ok']:
                    self.logger.warning(res['payload'])
                    # TODO return or continue?
                    return res
                if len(res['payload']) > 0:
                    oppArray.append(res['payload'][0])
            doc['products'] = oppArray

            res = self.getAccountProjects(accountId)
            if not res['ok']:
                self.logger.warning(res['payload'])
                return res
            doc['projects'] = res['payload']

        doc = self.convertFieldIllegals(doc)
        doc['_id'] = accountId
        self.db_support.salesforce.save(doc)
        return {'ok': True, 'payload': doc}

    ############
    # Karakuri #
    ############
    def setLive(self, b):
        """ Lock and load? """
        self.live = b

    def addSFPublicAccountNote(self, companyId, title, comment):
        res = self._getAccountId(companyId)
        if not res['ok']:
            return res
        sfId = res['payload']
        return self.addSFNote(sfId, title, comment, False)

    def addSFPrivateAccountNote(self, companyId, title, comment):
        res = self._getAccountId(companyId)
        if not res['ok']:
            return res
        sfId = res['payload']
        return self.addSFNote(sfId, title, comment, True)

    def addSFPublicProjectNote(self, companyId, title, comment):
        res = self._getProjectId(companyId)
        if not res['ok']:
            return res
        sfId = res['payload']
        return self.addSFNote(sfId, title, comment, False)

    def addSFPrivateProjectNote(self, companyId, title, comment):
        res = self._getProjectId(companyId)
        if not res['ok']:
            return res
        sfId = res['payload']
        return self.addSFNote(sfId, title, comment, True)

    def addSFNote(self, sfId, title, comment, isPrivate):
        """ This method adds a note to an SObject """
        self.logger.info("Adding note to %s" % sfId)

        note = {'type': 'Note',
                'Title': title,
                'Body': comment,
                'IsPrivate': isPrivate,
                'ParentId': sfId
                }

        res = self._create(note)
        if not res['ok']:
            return res
        res = res['payload']

        if res[0]['success'] is True:
            self.logger.info("Created note %s" % res[0]['id'])
        else:
            msg = 'Failed to create note: {0}'.format(res[0]['errors'])
            self.logger.warning(msg)
            return {'ok': False, 'payload': msg}
        return {'ok': True, 'payload': res[0]}

    def _create(self, fields):
        """ Create an object in SalesForce """
        # Unfortunately, pyforce does not yet support describeSObject, so there
        # is no way to dynamically determine the required fields. Until this
        # functionality exists go to the SalesForce API reference and maek your
        # best guess: https://www.salesforce.com/developer/docs/api/

        # A quick validation that type is defined
        if 'type' not in fields:
            return {'ok': False,
                    'payload': 'Unable to create, type not defined'}

        try:
            res = self.sfdc.create(fields)
        except Exception as e:
            raise(e)

        return {'ok': True, 'payload': res}

    def _delete(self, sfId):
        """ Delete an object in SalesForce """
        try:
            res = self.sfdc.delete(sfId)
        except Exception as e:
            raise(e)

        return {'ok': True, 'payload': res}

    def _update(self, fields):
        """ Update an object in SalesForce """

        # A quick validation that type is defined
        if 'type' not in fields:
            return {'ok': False,
                    'payload': 'Unable to create, type not defined'}

        try:
            res = self.sfdc.update(fields)
        except Exception as e:
            raise(e)

        return {'ok': True, 'payload': res}

    def editSFNote(self, sfId, comment):
        """ This method updates an existing Salesforce note """
        self.logger.debug("editSFNote('%s','%s')", sfId, comment)
        note = {'Id': sfId, 'type': 'Note', 'Body': comment}
        return self._update(note)

    def deleteSFNote(self, sfId):
        """ This method deletes an existing Salesforce note """
        self.logger.debug("deleteSFNote('%s')", sfId)
        return self._delete(sfId)

    def _getId(self, companyId, type):
        """ Return the SF id of the given type """
        match = {'_id': companyId}

        try:
            doc = self.db_support.companies.find_one(match)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}

        if doc is None:
            return {'ok': False, 'payload': 'Company %s not found' % companyId}

        idField = "sf_%s_id" % type
        if idField not in doc:
            return {'ok': False, 'payload': 'Company %s does not have field %s'
                    % (companyId, idField)}
        return {'ok': True, 'payload': doc.get('sf_%s_id' % type)}

    def _getAccountId(self, companyId):
        return self._getId(companyId, "account")

    def _getProjectId(self, companyId):
        return self._getId(companyId, "project")

if __name__ == "__main__":
    desc = "Salesforce Plus Plus"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                                    "(default=mongodb://localhost:27017)")
    parser.add_config_argument(
        "--sfdc-username", metavar="SFDC_USERNAME",
        help="specify a Salesforce username"
    )
    parser.add_config_argument(
        "--sfdc-password", metavar="SFDC_PASSWORD",
        help="specify a Salesforce password (prefix with security hash)"
    )
    parser.add_config_argument(
        "--timeout", metavar="SECONDS", default=0.1,
        help="specify the timeout between queries (default=0.1)"
    )
    parser.add_config_argument(
        "--query-type", metavar="QUERY_TYPE", default="all",
        choices=["all", "accountOnly"],
        help="specify the query type: all, accountOnly (default=all)"
    )
    parser.add_config_argument(
        "--query-who", metavar="QUERY_WHO",
        choices=["all", "csOnly"],
        help="specify the category of customer to query: all, csOnly; this "
             "overrides any sids specified"
    )
    parser.add_argument(
        "sid", nargs='*',
        help="<-- the Salesforce account id(s) to query"
    )
    args = parser.parse_args()

    if args.query_who is None and len(args.sid) == 0:
        print("Please specify Salesforce account id(s) to query")
        sys.exit(1)

    sfdc = sfdcpp(args)
    sfdc.run()
    sys.exit(0)
