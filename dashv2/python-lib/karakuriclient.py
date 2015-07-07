import argumentparserpp
import bson.json_util
import logging
import requests


class karakuriclient:
    """ A base class for karakuri clients """
    def __init__(self, args):
        # Expect args from karakuriclientparser
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

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

        self.token = self.args['token']

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

    def getToken(self):
        return self.token

    def issueRequest(self, issue=None, command=None, arg=None, **kwargs):
        endpoint = '/issue'
        return self.getRequest(endpoint, issue, command, arg, **kwargs)

    def postRequest(self, endpoint, entity=None, data=None, **kwargs):
        if entity is not None:
            endpoint += '/%s' % entity
        return self.request(endpoint, "POST", data, **kwargs)

    def queueRequest(self, command=None, arg=None, **kwargs):
        endpoint = '/queue'
        return self.getRequest(endpoint, None, command, arg, **kwargs)

    def request(self, endpoint, method="GET", data=None, **kwargs):
        self.logger.debug("request(%s,%s,%s)", endpoint, method, data)
        url = "http://%s:%i%s" % (self.args['karakuri_host'],
                                  self.args['karakuri_port'], endpoint)
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
            message = 'karakuri: %s' % e
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

    def taskRequest(self, task=None, command=None, arg=None, **kwargs):
        endpoint = '/task'
        return self.getRequest(endpoint, task, command, arg, **kwargs)

    def tasksRequest(self, tasks, command=None, arg=None, **kwargs):
        _tasks = []
        for task in tasks:
            res = self.taskRequest(task, command, arg, **kwargs)
            if res['status'] == 'success':
                if res['data']['task'] is not None:
                    _tasks.append(res['data']['task'])
            else:
                return res
        return {'status': 'success', 'data': {'tasks': _tasks}}

    def userRequest(self, token=None, command=None, arg=None, **kwargs):
        endpoint = '/user'
        return self.getRequest(endpoint, token, command, arg, **kwargs)

    def workflowRequest(self, workflow=None, command=None, arg=None, **kwargs):
        endpoint = '/workflow'
        output = self.getRequest(endpoint, workflow, command, arg, **kwargs)
        return output

    def workflowsRequest(self, workflows, command=None, arg=None, **kwargs):
        _workflows = []
        for workflow in workflows:
            res = self.workflowRequest(workflow, command, arg, **kwargs)
            if res['status'] == 'success':
                if res['data']['workflow'] is not None:
                    _workflows.append(res['data']['workflow'])
            else:
                return res
        return {'status': 'success', 'data': {'workflows': _workflows}}


class karakuriclientparser(argumentparserpp.CliArgumentParser):
    def __init__(self, *args, **kwargs):
        argumentparserpp.CliArgumentParser.__init__(self, *args, **kwargs)
        self.add_config_argument("--karakuri-host", metavar="HOSTNAME",
                                 default="localhost",
                                 help="specify the karakuri hostname "
                                      "(default=localhost)")
        self.add_config_argument("--karakuri-port", metavar="PORT", type=int,
                                 default=8080,
                                 help="specify the karakuri port "
                                      "(default=8080)")
        self.add_config_argument("--token", metavar="TOKEN",
                                 help="specify a user token to persist")
