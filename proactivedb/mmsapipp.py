#!/usr/bin/env python
import argumentparserpp
import base64
import bson
import bson.json_util
import bson.binary
import logging
import pymongo
import urllib2
import time
import sys
import zlib


class mmsapipp:
    def __init__(self, args):
        if not isinstance(args, dict):
            args = vars(args)
        self.args = args

        logging.basicConfig(format='%(asctime)s - %(module)s - %(levelname)s -'
                                   ' %(message)s')
        self.logger = logging.getLogger("logger")
        self.logger.setLevel(self.args['log_level'])
        fh = logging.FileHandler(self.args['log'])
        self.logger.addHandler(fh)

        self.logger.debug(self.args)

        # Initialize dbs and collections
        try:
            self.mongo = pymongo.MongoClient(self.args['mongo_uri'])
        except pymongo.errors.PyMongoError as e:
            self.logger.exception(e)
            raise e

        self.db_euphonia = self.mongo.euphonia

    def queryMMSAPI(self, uri):
        # wait a spell so as not to piss off the MMS folk [too much]
        time.sleep(self.args['timeout'])

        auth_handler = urllib2.HTTPDigestAuthHandler()
        url = 'https://cloud.mongodb.com/api/public/v1.0'
        # if uri is a full url, use it
        if uri.startswith('https://'):
            url = uri
        else:
            url = '%s%s' % (url, uri)
        self.logger.info(url)
        auth_handler.add_password(realm="MMS Public API",
                                  uri=url,
                                  # TODO move to config
                                  user=self.args['mmsapi_user'],
                                  passwd=self.args['mmsapi_token'])
        opener = urllib2.build_opener(auth_handler)

        try:
            f = opener.open(url)
        except Exception as e:
            return {'ok': False, 'payload': e}

        s = f.read()

        try:
            res = bson.json_util.loads(s)
        except Exception as e:
            self.logger.exception(e)
            return {'ok': False, 'payload': e}

        # cool story, the results may be paginated
        # if there's a 'next' link load that and append the result
        if 'results' in res:
            results = []
            results += res['results']
            links = res['links']
            for link in links:
                if link['rel'] == "next":
                    res = self.queryMMSAPI(link['href'])
                    if res['ok']:
                        results += res['payload']['results']
            res['results'] = results
        return {'ok': True, 'payload': res}

    def getGroups(self):
        return self.queryMMSAPI('/groups')

    def getGroup(self, groupId):
        return self.queryMMSAPI('/groups/%s' % groupId)

    def getGroupHosts(self, groupId):
        res = self.queryMMSAPI('/groups/%s/hosts' % groupId)
        if not res['ok']:
            return res
        return {'ok': True, 'payload': res['payload']['results']}

    def getGroupHost(self, groupId, hostId):
        return self.queryMMSAPI('/groups/%s/hosts/%s' % (groupId, hostId))

    def getGroupHostLastPing(self, groupId, hostId):
        return self.queryMMSAPI('/groups/%s/hosts/%s/lastPing' %
                                (groupId, hostId))

    def getGroupLastPing(self, groupId):
        return self.queryMMSAPI('/groups/%s/lastPing' % groupId)

    def compress(self, doc):
        try:
            doc = bson.json_util.dumps(doc)
        except Exception as e:
            self.logger.exception(e)

        try:
            doc = base64.b64encode(doc)
        except Exception as e:
            self.logger.exception(e)

        try:
            doc = zlib.compress(doc)
        except Exception as e:
            self.logger.exception(e)

        try:
            doc = bson.Binary(doc)
        except Exception as e:
            self.logger.exception(e)
        return doc

    # TODO move this to a common lib?
    def _convertFieldIllegals(self, doc):
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
                doc[key] = self._convertFieldIllegals(val)
            elif isinstance(val, list):
                newVal = []
                for item in val:
                    if isinstance(item, dict):
                        newVal.append(self._convertFieldIllegals(item))
                    else:
                        newVal.append(item)
                    # NOTE lack of list-check here means we only go one array
                    # deep in performing the conversion
                doc[key] = newVal
        return doc

    def getListOfGroupIds(self, activeAgentCountGT0=True):
        res = self.getGroups()
        if not res['ok']:
            self.logger.warning(res['payload'])
            return res
        groups = res['payload']['results']

        groupIds = []
        for group in groups:
            if activeAgentCountGT0 and group['activeAgentCount'] > 0:
                groupIds.append(group['id'])
        return {'ok': True, 'payload': groupIds}

    def run(self):
        if self.args['query_who'] == 'all':
            # all groups
            res = self.getListOfGroupIds()
            if not res['ok']:
                self.logger.warning(res['payload'])
                return res
            self.args['gid'] = res['payload']
        self.logger.info("Querying %s groups", len(self.args['gid']))
        i = 0
        for gid in self.args['gid']:
            i += 1
            if (i + 1) % 10 == 0:
                self.logger.info("... %i (%.2f %%)", i+1,
                                 float(i+1)*100./len(self.args['gid']))
            if self.args['query_type'] == "all":
                res = self.saveGroup(gid)
                if not res['ok']:
                    self.logger.warning(res['payload'])
            elif self.args['query_type'] == "groupOnly":
                res = self.saveGroupHighLevel(gid)
                if not res['ok']:
                    self.logger.warning(res['payload'])
            elif self.args['query_type'] == "pingsOnly":
                res = self.saveGroupLastPing(gid)
                if not res['ok']:
                    self.logger.warning(res['payload'])
            else:
                self.logger.warning("Unknown query_type specified")
                sys.exit(3)

    def saveGroup(self, groupId):
        res = self.saveGroupHighLevel(groupId)
        if not res['ok']:
            self.logger.warning(res['payload'])
            return res
        doc = res['payload']
        groupName = doc['name']
        # pings don't include group name but we want to propagate them :(
        return self.saveGroupLastPing(groupId, groupName)

    def saveGroupHighLevel(self, groupId):
        res = self.getGroup(groupId)
        if not res['ok']:
            return res
        doc = res['payload']
        _id = doc['id']
        del doc['id']
        if 'links' in doc:
            del(doc['links'])

        try:
            doc = self.db_euphonia.groups.find_and_modify(query={'_id': _id},
                                                          update={"$set": doc},
                                                          upsert=True,
                                                          new=True)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}
        return {'ok': True, 'payload': doc}

    def saveGroupLastPings(self, groupId, groupName, hosts=None):
        if hosts is None:
            res = self.getGroupHosts(groupId)
            if not res['ok']:
                return res
            hosts = res['payload']

        # used to identify pings fetched in this particular call to
        # getGroupLastPings; in essence, it defines what is a group
        tag = bson.ObjectId()

        for host in hosts:
            # don't bother with deactivated hosts
            if host.get('deactivated', False) is True:
                continue
            res = self.getGroupHostLastPing(groupId, host['id'])
            if not res['ok']:
                res['payload'] = {'ping': None}
            ping = res['payload']['ping']

            doc = {'gid': groupId, 'name': groupName, 'hid': host['id'],
                   'tag': tag, 'ts': tag.generation_time, 'doc': ping,
                   'hostInfo': host}
            self.saveLastPing(doc)
        return {'ok': True, 'payload': []}

    def saveGroupLastPing(self, groupId, groupName):
        # unfortunately, we need this to do hid <-> hostname:port matching
        res = self.getGroupHosts(groupId)
        if not res['ok']:
            return res
        hosts = res['payload']

        res = self.getGroupLastPing(groupId)
        if not res['ok']:
            self.logger.warning(res['payload'])
            # try individual hosts before giving up
            return self.saveGroupLastPings(groupId, groupName, hosts)
        ping = res['payload']['ping']

        # hid and host:port lookups
        hid2host = {}
        hostnameport2hid = {}
        for host in hosts:
            hid2host[host['id']] = host
            key = "%s:%s" % (host['hostname'], host['port'])
            hostnameport2hid[key] = host['id']

        if ping is not None:
            # used to identify pings fetched in this particular call to
            # getGroupLastPing; in essence, it defines what is a group
            tag = bson.ObjectId(ping["_id"])

            hostPings = ping['d']['hosts']
            for hostKey in hostPings:
                hostPing = hostPings[hostKey]
                if len(hostPing) == 0:
                    # this host's last ping is not in the group last ping
                    # would be nice to fetch it from the hosts endpoint but we
                    # can't because we don't have the hostId :(
                    self.logger.debug("len(hostPing) == 0")
                    self.logger.debug(hostPing)
                    continue
                if 'host' not in hostPing or 'port' not in hostPing:
                    # there is no way to identify this guy by hid so skip
                    self.logger.debug("host or port not in hostPing")
                    self.logger.debug(hostPing)
                    continue
                hostnameport = "%s:%s" % (hostPing['host'], hostPing['port'])
                if hostnameport in hostnameport2hid:
                    hid = hostnameport2hid[hostnameport]
                else:
                    # If this happens then there is some asymmetry between
                    # what's stored in the group lastPing and what's given
                    # at groups/GROUPID/hosts that needs an MMSP
                    self.logger.warning("Could not determine hostId for %s",
                                        hostnameport)
                    hid = None
                # don't bother if we know the host is deactivated
                host = hid2host.get(hid)
                if host is not None and host.get('deactivated', False) is True:
                    continue
                doc = {'gid': groupId, 'name': groupName, 'hid': hid,
                       'tag': tag, 'ts': tag.generation_time, 'doc': hostPing,
                       'hostInfo': host}
                self.saveLastPing(doc)
        return {'ok': True, 'payload': []}

    def saveLastPing(self, ping):
        # find all fields containing '.' and convert to '\p'
        if ping['doc'] is not None:
            # ensure ping is valid for insertion
            ping['doc'] = self._convertFieldIllegals(ping['doc'])
            # compress unruly documents
            if 'dbProfileData' in ping['doc']:
                self.logger.info("Compressing dbProfileData document")
                ping['doc']['dbProfileData'] = self.compress(
                    ping['doc']['dbProfileData'])
        try:
            self.db_euphonia.pings.insert(ping)
        except pymongo.errors.PyMongoError as e:
            return {'ok': False, 'payload': e}

if __name__ == "__main__":
    desc = "MMS API Plus Plus"
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                                    "(default=mongodb://localhost:27017)")
    parser.add_config_argument(
        "--mmsapi-user", metavar="MMSAPI_USER",
        help="specify an MMS API user"
    )
    parser.add_config_argument(
        "--mmsapi-token", metavar="MMSAPI_TOKEN",
        help="specify an MMS API token"
    )
    parser.add_config_argument(
        "--timeout", metavar="SECONDS", default=0.1,
        help="specify the timeout between queries (default=0.1)"
    )
    parser.add_config_argument(
        "--query-type", metavar="QUERY_TYPE", default="all",
        choices=["all", "groupOnly", "pingsOnly"],
        help="specify the query type: all, groupOnly, pingsOnly (default=all)"
    )
    parser.add_config_argument(
        "--query-who", metavar="QUERY_WHO",
        choices=["all", "csOnly"],
        help="specify the category of MMS groups to query: all, csOnly; this "
             "overrides any gids specified"
    )
    parser.add_argument(
        "gid", nargs='*',
        help="<-- the MMS group id(s) to query"
    )
    args = parser.parse_args()

    if args.query_who is None and len(args.gid) == 0:
        print("Please specify MMS group id(s) to query")
        sys.exit(1)

    mms = mmsapipp(args)
    mms.run()
    sys.exit(0)
