import bson.json_util
import logging
import requests
import time

""" ------------------------------------------------------------------------ #
A nifty little client for interacting with the support api restful interface.
# ------------------------------------------------------------------------ """


class stAPIclient:
    """ A base class for all support api (stAPI) requests """
    def __init__(self, args):
        # Expect args from stapiclientparser
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        self.token = "default"

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

    """ -------------------------------------------------------------------- #
    # These are the base API functions that I could think of people (including
    # myself) potentially needing. Feel free to add/suggest more if you think
    # of more use cases.
    # -------------------------------------------------------------------- """
    # Public API function
    # @staticmethod # I want to eventually implement these as static methods
    def addReviewerSelf(self, id, method="PUT", **kwargs):
        endpoint = '/reviews/' + id + '/reviewer/self'
        return self._request(endpoint, **kwargs)

    def addLookingSelf(self, id, method="PUT", **kwargs):
        endpoint = '/reviews/' + id + '/looking/self'
        return self._request(endpoint, **kwargs)

    def removeReviewerSelf(self, id, method="PUT", **kwargs):
        endpoint = '/reviews/' + id + '/unreview/self'
        return self._request(endpoint, **kwargs)

    def removeLookingSelf(self, id, method="PUT", **kwargs):
        endpoint = '/reviews/' + id + '/unlooking/self'
        return self._request(endpoint, **kwargs)

    def getActiveIssues(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['active'] = "true"
        params['support'] = "true"
        return self._request(endpoint, params=params, **kwargs)

    def getActiveFTSs(self, **kwargs):
        endpoint = '/issues/summary/fts'
        params = {}
        return self._request(endpoint, params=params, **kwargs)

    def getActiveReviews(self, **kwargs):
        endpoint = '/reviews'
        params = {}
        params['active'] = "true"
        return self._request(endpoint, params=params, **kwargs)

    def getActiveSLAs(self, **kwargs):
        endpoint = '/issues/summary/sla'
        params = {}
        return self._request(endpoint, params=params, **kwargs)

    def getActiveUNAs(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['una'] = "true"
        params['support'] = "true"
        params['active'] = "true"
        return self._request(endpoint, params=params, **kwargs)

    def getAssignedIssues(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['support'] = "true"
        params['usr_assigned'] = "true"
        params['active'] = "true"
        return self._request(endpoint, params=params, **kwargs)

    def getUpdatedIssues(self, last_updated, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['last_updated'] = last_updated
        params['support'] = "true"
        return self._request(endpoint, params=params, **kwargs)

    def getUNAs(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['una'] = "true"
        params['support'] = "true"
        params['active'] = "true"
        params['wait'] = "true"
        return self._request(endpoint, params=params, **kwargs)

    def getUserInfo(self, token, **kwargs):
        endpoint = "/login"
        params = {}
        params['token'] = token
        return self._request(endpoint, params=params, **kwargs)

    def getWaitingIssues(self, **kwargs):
        endpoint = '/issues/summary'
        params = {}
        params['wait'] = "true"
        params['support'] = "true"
        return self._request(endpoint, params=params, **kwargs)

    """ -------------------------------------------------------------------- #
    # These are private functions for the stapiclient to handle API requests.
    # They shouldn't be available/used by the application directly.
    # --------------------------------------------------------------------- """

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
        headers['Content-Type'] = 'application/json'
        params = kwargs.get('params', None)

        self.logger.debug("Time before http request : " + str(
            time.time() % 10) + "\n")

        try:
            res = requests.request(method, url, params=params,
                                    headers=headers, data=data)
        except requests.adapters.ConnectionError as e:
            self.logger.exception(e)
            message = 'stapi: %s' % e
            return {'status': 'error', 'payload': str(message)}

        self.logger.debug("Time to after http request: " + str(
            time.time() % 10) + "\n")

        if res is not None:
            if res.status_code == requests.codes.ok:
                try:
                    return {'status': 'success', 'payload':
                            bson.json_util.loads(res.content)['data']}
                except Exception as e:
                    message = e
            elif res.status_code == 401:
                return {'status': 'error', 'payload':
                        'Unauthorized User. Please log into Corp.'}
            else:
                try:
                    ret = bson.json_util.loads(res.text)
                    message = str(ret['message'])
                except Exception as e:
                    message = str(e) + " at point [failure] in stapiclient._request()"
        else:
            message = "request(%s,%s) failed" % (endpoint, method)
        return {'status': 'error', 'payload': message}
