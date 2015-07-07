import argumentparserpp
import bson.json_util
import logging
import requests
import time
import urllib
from datetime import datetime, timedelta

""" --------------------------------------------------------------------------- #
# AVAILABLE: These are the functions that are available to use at the moment
#
#   -find(self, collection, query, proj) :: the general find function
#       for querying the database.
#       args:
#           collection - name of a collection in support database
#           query - None by default. Will return all documents if no
#               query is specified. 
#           proj - None by default. Projection for the query
#       returns : document[] - array of documents
#
#   -getActiveReviews() :: returns all reviews with {"done" : False}
#       args: None
#       returns : document[] - array of reviews
#
# TO ADD: Here are the functions that I plan on adding/am in the process of
# adding
#   -get/set token
#   -get/set user
#   -create/delete user
#   -update issue/review - I am conflicted here as to whether to make
#       these separate functions, or make them one generalized function
#       that takes a collection as an argument. As of now, I'll probably just
#       make both and allow the application to decide what to use.
#   -create/delete issue/review? - I know the bot will need this
#       functionality, but I can wait for input from Neal on how he 
#       wants this implemented.
#   -finally, there are a ton of karakuri/euphonia functions that deal with 
#       the workflow interface. I'll wait till a discussion with jake 
#       to transfer these over
# --------------------------------------------------------------------------- """


class stAPIclient:
    """ A base class for all support api (stAPI) requests """
    def __init__(self, args):
        # Expect args from karakuriclientparser
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args
        self.token = None

        # Log what your mother gave you
        logging.basicConfig()
        self.logger = logging.getLogger('logger')
        self.logger.setLevel(self.args['log_level'])

        # Output args for debugging
        self.logger.debug("parsed args:")
        for arg in self.args:
            if "password" in arg or "passwd" in arg or "token" in arg:
                tmp = "[REDACTED]"
            else:
                tmp = self.args[arg]
            self.logger.debug("%s %s" % (arg, tmp))

    
    """ ----------------------------------------------------------------------- #
    # These are the base API functions that I could think of people (including
    # myself) potentially needing. Feel free to add/suggest more if you think
    # of more use cases.
    # ----------------------------------------------------------------------- """
            
    # Public API function
    # @staticmethod
    def getActiveReviews(self, **kwargs):
        endpoint = '/reviews'
        params = {}
        params['active'] = "true"
        return self._getRequest(endpoint, params=params, **kwargs)#['data']#['reviews']

    def getActiveIssues(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['active'] = "true"
        params['dash'] = "true"
        return self._getRequest(endpoint, params=params, **kwargs)

    def getActiveFTSs(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['fts'] = "true"
        params['dash'] = "true"
        return self._getRequest(endpoint, params=params, **kwargs)

    def getActiveSLAs(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['sla'] = "true"
        params['dash'] = "true"
        return self._getRequest(endpoint, params=params, **kwargs)

    def getActiveUNAs(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['una'] = "true"
        params['dash'] = "true"
        return self._getRequest(endpoint, params=params, **kwargs)

    def getUpdatedIssues(self, last_updated, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['last_updated'] = last_updated
        params['dash'] = "true"
        return self._getRequest(endpoint, params=params, **kwargs)

    """ ----------------------------------------------------------------------- #
    # These are private functions for the stapiclient to handle API requests.
    # They shouldn't be available/used by the application directly.
    # ------------------------------------------------------------------------ """

    """this function seems pointless at this point. Consider removing"""
    def _getRequest(self, endpoint, entity=None, command=None, arg=None,
                   **kwargs):
        if entity is not None:
            endpoint += '/%s' % entity
        if command is not None:
            endpoint += '/%s' % command
            if arg is not None:
                endpoint += '/%s' % arg
        return self._request(endpoint, **kwargs)

    def _request(self, endpoint, method="GET", data=None, **kwargs):
        self.logger.debug("request(%s,%s,%s)", endpoint, method, data)
        url = "http://%s:%i%s" % (self.args['stapi_host'],
                                  self.args['stapi_port'], endpoint)
        if 'token' in kwargs:
            token = kwargs['token']
        else:
            token = self.token
        headers = {'Accept-Encoding': 'compress, gzip, deflate, identity',
                   'Authorization': "usr_token=%s" % token}
        params = kwargs.get('params', None)
        # col = kwargs.get('col', None)
        # query = kwargs.get('query', None)
        # proj = kwargs.get('proj', None)

        # if col is not None:
        #     params['col'] = col
        # if query is not None:
        #     params['query'] = query
        # if proj is not None:
        #     params['proj'] = proj

        now = datetime.utcnow()

        self.logger.info("Time before http request : " + str(time.time() % 10) + "\n")

        try:
            res = requests.request(method, url, params=params, headers=headers, data=data)
        except requests.adapters.ConnectionError as e:
            self.logger.exception(e)
            message = 'stapi: %s' % e
            return {'status': 'error', 'message': message}

        self.logger.info("Time to after http request: " + str(time.time() % 10) + "\n")

        # self.logger.info(res.content)

        if res is not None:
            if res.status_code == requests.codes.ok:
                try:
                    # ret = bson.json_util.loads(res.text)['data']
                    # ret = res.content
                    # self.logger.info(res.content)
                    return bson.json_util.loads(res.content)['data']
                except Exception as e:
                    message = e
            else:
                try:
                    ret = bson.json_util.loads(res.text)
                    message = ret['message']
                except Exception as e:
                    message = e
        else:
            message = "request(%s,%s) failed" % (endpoint, method)
        return {'status': 'error', 'message_here': message}