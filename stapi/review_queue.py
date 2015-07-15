#!/usr/bin/env python

import argumentparserpp
# from pymongo import MongoClient
import pymongo
import os
import datetime
from ConfigParser import RawConfigParser
from pprint import pprint


class ReviewQueue:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _build_id_query(ident):
        """builds query on _id"""
        query = {'_id': ident}
        return query

    @staticmethod
    def _build_review_list(cursor):
        """iterates over mongodb cursor, returning array of results"""
        review_list = []
        for review in cursor:
            review['review_id'] = review['_id']
            del review['_id']
            review_list.append(review)

        return review_list

    @staticmethod
    def _build_result_doc(review_list):
        """Packages a review list and into a client-parsable result doc"""
        doc = {}
        doc['type'] = 'review'
        doc['review_list'] = review_list

        return doc

    def _retrieve_issue_by_id(self, issue_id):
        cursor = self.db.issues.find({'ticket_id.jira': issue_id})

        if (cursor.count() == 0):
            return None

        return cursor[0]

    def _retrieve_issue_by_key(self, issue_key):
        cursor = self.db.issues.find({'jira.key': issue_key})

        if (cursor.count() == 0):
            return None

        return cursor[0]

    def _add_issue_detail(self, review_list):
        """Retrieve the issue details, including unique ID (for lookup)
        """
        for review in review_list:
            review['issue'] = {}

            issue = self._retrieve_issue_by_key(review['key'].encode(
                'utf-8').strip().upper())

            if (issue is not None):
                review['issue']['issue_id'] = issue['jira']['id']
                if ('assignee' in issue['jira']['fields'] and
                        issue['jira']['fields']['assignee'] is not None):
                    review['issue']['assignee'] = {}

                    if ("name" in issue['jira']['fields']['assignee']):
                        review['issue']['assignee']['id'] = \
                            issue['jira']['fields']['assignee']['name']

                    if ("displayName" in issue['jira']['fields']['assignee']):
                        review['issue']['assignee']['name'] = \
                            issue['jira']['fields']['assignee']['displayName']
                else:
                    review['issue']['assignee'] = None

                review['issue']['active'] = issue['dash']['active']['now']

                if 'sla' in issue:
                    review['issue']['sla'] = issue['sla']
                else:
                    review['issue']['sla'] = None

            else:
                review['issue']['issue_id'] = None
                review['issue']['assignee'] = None
                review['issue']['active'] = None
                review['issue']['sla'] = None

    def _build_review_request(self, key):
        """Builds and returns a review request document. If an active
        review already exists then it is retrieved and reset for the
        new review request.
        """
        cursor = self.db.reviews.find({'key': key, 'done': {'$ne': True}})

        review_doc = {}

        if (cursor.count() != 0):
            review_doc = cursor[0]
            # TODO: We should notify existing reviewers that this review is
            #       ready for another look
        else:
            # 'key' refers to the Jira key which changes when a Jira issue
            # is moved. The dashboard prefers the Jira ID but we use key
            # here for Bot compatability
            review_doc['key'] = key
            review_doc['reviewers'] = []

        review_doc['done'] = False
        review_doc['status'] = 'requested'
        review_doc['lgtms'] = []
        review_doc['marked_by'] = ''

        return review_doc

    def _add_missing_requestat_ts(self, review_list):
        """TSPROJ-8 requests that the bot record a "requested_at" timestamp
        on review creation. As a workaround in the interim this method
        will create and write back a timestamp when missing.
        """
        for review in review_list:
            if "requested_at" not in review:
                now = datetime.datetime.utcnow()
                review['requested_at'] = now
                self.db.reviews.update({'_id': review['review_id']}, {'$set': {'requested_at': now}})


    def get_active_review_list(self):
        """Returns a document containing all active reviews. This includes
        a "type" field for use by client to identify contents.
        """

        #TODO: The SupportBot overloads the 'done' field by writing a string
        #      when "#!NEEDSWORK" is requested. In all other cases this field
        #      contains a boolean. We need to support this behavior until the
        #      bot is changed.
        query = {'done': {'$in': [False, 'needs work']}}
        cursor = self.db.reviews.find(query)

        review_list = self._build_review_list(cursor)

        self._add_missing_requestat_ts(review_list)

        self._add_issue_detail(review_list)

        doc = self._build_result_doc(review_list)

        return doc

    def add_lgtm(self, request):
        """Adds requestor LGTM to review"""
        #TODO: May be worth having a list of approved reviewers and modifying
        #      status to "approved" on in cases where there is an approved
        #      reviewer
        query = self._build_id_query(request['review_id'])
        action = {'$set': {'status': 'approved'},
                  '$addToSet': {'lgtms': request['who']}}
        result = self.db.reviews.update(query, action)

        if (result['n'] != 1):
            msg = "add_lgtm failed for {0}".format(request)
            raise Exception(msg)

    def request_review(self, request):
        """Request review for an issue. This will maintain any reviewers
        assigned to an existing request but will clear the LGTMs
        """
        issue_id = request['issue_id']
        issue = self._retrieve_issue_by_id(issue_id)

        if (issue is None):
            msg = "Cannot create review - unknown issue ID: {0}".format(
                issue_id)
            print msg
            raise Exception(msg)

        review_doc = self._build_review_request(issue['jira']['key'])
        review_doc['requested_by'] = request['requested_by']

        review_id = self.db.reviews.save(review_doc)

        if (review_id is None):
            msg = "save failed for review request: {0}".format(request)
            print(msg)
            raise Exception(msg)

        review_doc['review_id'] = review_id

        return review_doc

    def add_reviewer(self, request):
        """Add an individual to the list of reviewers for a given review"""
        reviewer = request['reviewer']
        review_id = request['review_id']

        # query = self._build_id_query(review_id)
        query = {'key': review_id}
        action = {'$addToSet': {'reviewers': reviewer}}
        result = self.db.reviews.update(query, action)

        if (result['n'] != 1):
            msg = "add_reviewer failed for {0}".format(request)
            raise Exception(msg)

    def remove_reviewer(self, request):
        """ Remove a reviewer from a given review"""
        reviewer = request['reviewer']
        review_id = request['review_id']

        # query = self._build_id_query(review_id)
        query = {'key': review_id}
        action = {'$pull': {'reviewers': reviewer}}
        result = self.db.reviews.update(query, action)

        if (result['n'] != 1):
            msg = "remove_reviewer failed for {0}".format(request)
            raise Exception(msg)

    def add_looking(self, request):
        """Add an individual to the list of looking for a given review"""
        looker = request['looker']
        review_id = request['review_id']

        # query = self._build_id_query(review_id)
        query = {'key': review_id}
        action = {'$addToSet': {'looking': looker}}
        result = self.db.reviews.update(query, action)

        if (result['n'] != 1):
            msg = "add_looking failed for {0}".format(request)
            raise Exception(msg)

    def remove_looking(self, request):
        """ Remove a looker from a given review"""
        looker = request['looker']
        review_id = request['review_id']

        # query = self._build_id_query(review_id)
        query = {'key': review_id}
        action = {'$pull': {'looking': looker}}
        result = self.db.reviews.update(query, action)

        if (result['n'] != 1):
            msg = "remove_looking failed for {0}".format(request)
            raise Exception(msg)

    def close_review(self, request):
        """Close the given review"""
        review_id = request['review_id']
        closed_by = request['closed_by']

        query = self._build_id_query(review_id)
        action = {'$set': {'done': True, 'status': 'closed',
                  'marked_by': closed_by}}
        result = self.db.reviews.update(query, action)

        if (result['n'] != 1):
            msg = "close_review failed for {0}".format(request)
            raise Exception(msg)

    def needs_work(self, request):
        """Mark given review as needing work"""
        review_id = request['review_id']
        marked_by = request['marked_by']

        query = self._build_id_query(review_id)
        action = {'$set': {'status': 'needs work', 'done': 'needs work',
                  'marked_by': marked_by}}
        result = self.db.reviews.update(query, action)

        if (result['n'] != 1):
            msg = "needs_work failed for {0}".format(request)
            raise Exception(msg)


def main():
    desc = "Tests for the review queue functions"

    parser = argumentparserpp.CliArgumentParser(description=desc)

    parser.add_config_argument("--jira-password", metavar="PASSWORD",
                               help="specify a JIRA password")
    parser.add_config_argument("--jira-username", metavar="USERNAME",
                               help="specify a JIRA username")
    parser.add_config_argument("--live", action="store_true",
                               help="do what you do irl")
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                                    "(default=mongodb://localhost:27017)")
    parser.add_config_argument("--pid", metavar="FILE",
                               default="/tmp/karakuri.pid",
                               help="specify a PID file "
                                    "(default=/tmp/karakuri.pid)")
    parser.add_config_argument("--rest-host",  metavar="HOST",
                               default="localhost",
                               help="the RESTful interface host "
                               "(default=localhost)")
    parser.add_config_argument("--rest-port",  metavar="PORT", default=8080,
                               type=int,
                               help="the RESTful interface port "
                                    "(default=8080)")
    parser.add_config_argument("--access-control-allowed-origins",
                               metavar="HOSTPORT",
                               help="comma separated list of origins allowed "
                                    "access control")
    parser.add_argument("command", choices=["start", "stop", "restart",
                                            "debug"],
                        help="<-- the available actions, choose one")
    args = parser.parse_args()

    mongo_uri = vars(args)['mongo_uri']

    db = pymongo.MongoClient(mongo_uri).support

    print('Test active review list retrieval')
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)

    print('\nTest request for review')
    insert_req = {'action': 'request_review'}
    insert_req['issue_id'] = '55118'
    insert_req['requested_by'] = 'james.create'
    inserted_doc = ReviewQueue(db).request_review(insert_req)
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)

    print ('\nTest Add Reviewer')
    add_rev_req = {'action': 'add_reviewer'}
    add_rev_req['review_id'] = inserted_doc['review_id']
    add_rev_req['reviewer'] = "james.reviewer"
    ReviewQueue(db).add_reviewer(add_rev_req)
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)

    print ('\nTest Needs Work')
    new_rev_req = {'action': 'needs_work'}
    new_rev_req['review_id'] = inserted_doc['review_id']
    new_rev_req['marked_by'] = "james.needs_work"
    ReviewQueue(db).needs_work(new_rev_req)
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)

    print('\nTest request for review (post needs work)')
    insert_req = {'action': 'request_review'}
    insert_req['issue_id'] = '55118'
    insert_req['requested_by'] = 'james.create2'
    inserted_doc = ReviewQueue(db).request_review(insert_req)
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)

    print('\nTest LGTM')
    lgtm_req = {'action': 'add_lgtm'}
    lgtm_req['action'] = 'lgtm'
    lgtm_req['review_id'] = inserted_doc['review_id']
    lgtm_req['who'] = 'james.lgtm'
    ReviewQueue(db).add_lgtm(lgtm_req)
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)

    print ('\nTest Remove Reviewer')
    rem_rev_req = {'action': 'remove_reviewer'}
    rem_rev_req['review_id'] = inserted_doc['review_id']
    rem_rev_req['reviewer'] = "james.reviewer"
    ReviewQueue(db).remove_reviewer(rem_rev_req)
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)

    print ('\nTest Close Review')
    close_rev_req = {'action': 'close_review'}
    close_rev_req['review_id'] = inserted_doc['review_id']
    close_rev_req['closed_by'] = "james.close"
    ReviewQueue(db).close_review(close_rev_req)
    review_list_doc = ReviewQueue(db).get_active_review_list()
    pprint(review_list_doc)


if __name__ == "__main__":
    main()
