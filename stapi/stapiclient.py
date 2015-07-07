import argumentparserpp
import bson.json_util
import logging
import requests


class stAPIclient:
    """ A base class for all support api (stAPI) requests clients """
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

    def deleteRequest(self, endpoint, entity=None, **kwargs):
        if entity is not None:
            endpoint += '/%s' % entity
        return self.request(endpoint, "DELETE", **kwargs)

    def getRequest(self, endpoint, entity=None, command=None, arg=None,
                   **kwargs):
        if entity is not None:
            endpoint += '/%s' % entity
        if command is not None:
            endpoint += '/%s' % command
            if arg is not None:
                endpoint += '/%s' % arg
        return self.request(endpoint, **kwargs)

    def issueRequest(self, issue=None, command=None, arg=None, **kwargs):
        endpoint = '/issue'
        return self.getRequest(endpoint, issue, command, arg, **kwargs)

    @staticmethod
    def getActiveReviews(**kwargs):
        endpoint = '/review/active'
        return self.getRequest(endpoint, **kwargs)

    def postRequest(self, endpoint, entity=None, data=None, **kwargs):
        if entity is not None:
            endpoint += '/%s' % entity
        return self.request(endpoint, "POST", data, **kwargs)

    def request(self, endpoint, method="GET", data=None, **kwargs):
        self.logger.debug("request(%s,%s,%s)", endpoint, method, data)
        url = "http://%s:%i%s" % (self.args['stapi_host'],
                                  self.args['stapi_port'], endpoint)
        if 'token' in kwargs:
            token = kwargs['token']
        else:
            token = self.token
        headers = {'Accept-Encoding': 'compress, gzip, deflate, identity',
                   'Authorization': "kk_token=%s" % token}
        try:
            res = requests.request(method, url, headers=headers, data=data)
        except requests.adapters.ConnectionError as e:
            self.logger.exception(e)
            message = 'stapi: %s' % e
            return {'status': 'error', 'message': message}

        if res is not None:
            if res.status_code == requests.codes.ok:
                try:
                    ret = bson.json_util.loads(res.content)
                    return ret
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
        return {'status': 'error', 'message': message}

    def setToken(self, token):
        self.token = token