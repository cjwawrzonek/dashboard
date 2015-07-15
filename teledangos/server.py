import argumentparserpp
import daemon
import logging
import os
import pidlockfile
import pymongo
import signal
import sys

from datetime import datetime, timedelta
from bottle import run, template, static_file, request, post, route
from bson.json_util import dumps
from supportissue import SupportIssue, isMongoDBEmail

# Timedelta has a new method in 2.7 that has to be hacked for 2.6
import ctypes as c

_get_dict = c.pythonapi._PyObject_GetDictPtr
_get_dict.restype = c.POINTER(c.py_object)
_get_dict.argtypes = [c.py_object]

try:
    timedelta.total_seconds
except AttributeError:
    def total_seconds(td):
        return float((td.microseconds +
                      (td.seconds + td.days * 24 * 3600) * 10**6)) / 10**6
    d = _get_dict(timedelta)[0]
    d['total_seconds'] = total_seconds

# -----------------------------------------------------------------------------
# APP ROUTES
# -----------------------------------------------------------------------------


@route('/js/<filename:re:.*\.js>')
def send_js(filename):
    return static_file(filename, root='./js', mimetype="text/javascript")


@route('/css/<filename:re:.*\.css>')
def send_css(filename):
    return static_file(filename, root='./css', mimetype="text/css")


@route('/fonts/<filename>')
def send_fonts(filename):
    return static_file(filename, root='./fonts')


@route('/dashboard')
def index():
    return template('dashboard')


@post('/ajax')
def ajax_response():
    try:
        client = pymongo.MongoClient(args.mongo_uri)
        support_db = client.support
    except pymongo.errors.PyMongoError as e:
        return dumps({"error": "Error connecting to MongoDB: " +
                      e.message})
    try:
        if (request.json and 'totals' in request.json):
            issues = getIssues(support_db, request.json)
        else:
            issues = getIssues(support_db, {})
    except Exception as err:
        logger.exception("Something went wrong in getIssues.")
        return dumps({"error": "Internal error: " + err.message})

    return dumps(issues)


# -----------------------------------------------------------------------------
# MAIN HELPERS
# -----------------------------------------------------------------------------


def getIssues(db, data):
    """The workhorse of refreshing the page. Given data, containing the
    currently displayed issues and the time they were last updated, update it
    to contain the issues that should appear on the dashboard.
    (SLA: Service Level Agreement, we are contractually obligated to respond in
         a certain amount of time to these issues, but haven't yet.
     FTS: Full Time Support, issues that need 24 hr monitoring. They are tagged
         as such in jira.
     REV: Reviews, issues needing review from peers. Stored in a separate
         collection in mongo.
     UNA: Unnassigned, issues with no assignee with the last comment made by a
         non-mongodb employee)"""
    start = datetime.utcnow()  # Time this and log how long refreshing took.
    try:
        cur = getRelevantIssues(db, data)
    except pymongo.errors.PyMongoError as e:
        return {"error": "Error querying the Mongo database: " +
                e.message}

    count = 0
    dbd_data = {
        # TODO: make sets of these to make the lookups below faster
        "SLA": data.get("SLA", []),
        "FTS": data.get("FTS", []),
        "REV": [],  # Just refresh these every time
        "UNA": data.get("UNA", []),
        "active": data.get("active", {}),
        "waiting": data.get("waiting", {})
    }

    try:
        revIssues = getREVIssues(db)
    except pymongo.errors.PyMongoError as e:
        return {"error": "Error querying the Mongo database: " +
                e.message}

    updated_data = {
        "SLA": [],
        "FTS": [],
        "REV": revIssues,
        "UNA": []
    }
    for i in cur:
        count += 1
        issue = SupportIssue().fromDoc(i)

        # Keep track of the totals:
        # --- Active issue count ---
        if issue.isActive():
            dbd_data['active'][issue.key] = 1
        elif issue.key in dbd_data['active']:
            del dbd_data['active'][issue.key]
        # --- Waiting For Customer issue count ---
        if issue.isWFC() and not issue.doc['deleted']:
            dbd_data['waiting'][issue.key] = 1
        elif issue.key in dbd_data['waiting']:
            del dbd_data['waiting'][issue.key]

        # For each category, see if the issue belongs, and if not, remove it
        # from the dashboard issues if it was there.
        if isSLA(issue):
            updated_data["SLA"].append(trimmedSLAIssue(issue))
        else:
            removeCompressedIssueIfPresent(issue, dbd_data["SLA"])
        if isFTS(issue):
            updated_data["FTS"].append(trimmedFTSIssue(issue))
        else:
            removeCompressedIssueIfPresent(issue, dbd_data["FTS"])
        if isUNA(issue):
            updated_data["UNA"].append(trimmedUNAIssue(issue))
        else:
            removeCompressedIssueIfPresent(issue, dbd_data["UNA"])

    mergeAndSortIssues(dbd_data, updated_data)

    duration = datetime.utcnow() - start
    logger.info("getIssues took {0}, count: {1}".format(duration, count))
    return dbd_data


def getRelevantIssues(db, data):
    """If updating dashboard, query for issues that have been updated since the
    last load. Otherwise query for all relevant issues. data will be empty if
    this is the first query."""
    last_updated = data.get('updated', None)
    query = {'$and': [
        {'jira.fields.issuetype.name': {'$nin': ['Tracking']}},
        {'jira.fields.project.key': {'$in': ['CS', 'MMSSUPPORT', 'SUPPORT',
                                             'PARTNER']}},
        ]
    }

    if last_updated is None:
        # Only filter the first time, since we want to know if issues on the
        # dashboard have closed
        query['$and'].append({'jira.fields.status.name': {
            '$in': ['Open', 'Reopened', 'In Progress',
                    'Waiting for Customer', 'Waiting For User Input']}
            }
        )
    else:
        query["$and"].append({"jira.fields.updated": {
            "$gte": last_updated
            }
        })

    # Only need these fields for determining if they belong, and displaying
    # them on the dashboard
    proj = {'_id': 0,
            'dash.active.now': 1,
            'deleted': 1,
            'jira.fields.assignee': 1,
            'jira.fields.created': 1,
            'jira.fields.issuetype': 1,
            'jira.fields.labels': 1,
            'jira.fields.priority.id': 1,
            'jira.fields.reporter': 1,
            'jira.fields.status': 1,
            'jira.fields.updated': 1,
            'jira.fields.comment.comments.author.emailAddress': 1,
            'jira.fields.comment.comments.created': 1,
            'jira.fields.comment.comments.updated': 1,
            'jira.fields.comment.comments.visibility': 1,
            'jira.key': 1,
            'jira.tags': 1,
            'sla': 1,
            }
    cur = db.issues.find(query, proj)
    cur.batch_size(100000)
    return cur


# -----------------------------------------------------------------------------
# FILTERS (decide which issues should be displayed on the dashboard)
# -----------------------------------------------------------------------------


def getREVIssues(db):
    """No fancy logic necessary here, just post all issues needing review."""
    return map(trimmedREVDoc,
               db.reviews.find({"done": False, "lgtms": {"$exists": False}}))


def isSLA(issue):
    """Return true if the issue should be displayed in the SLA row of the
    dashboard."""
    return (issue.isActive() and
            issue.hasSLA() and
            'expireAt' in issue.doc['sla'] and
            issue.doc['sla']['expireAt'] is not None and
            ((not issue.isProactive() and issue.firstXGenPublicComment is None)
                or (issue.isProactive() and
                    issue.firstXGenPublicCommentAfterCustomerComment is None)))


def isFTS(issue):
    """Return true if the issue should be displayed in the FTS row of the
    dashboard."""
    return (issue.isActive() and
            issue.isFTS())


def isUNA(issue):
    """Change: ticket qualifies as UNA if it is open, not an SLA, and has
    no assignee. Simple"""
    assignee = issue.doc["jira"]["fields"]["assignee"]
    if issue.lastXGenPublicComment is None and issue.hasSLA():
        # Will show up as an SLA
        return False
    elif issue.status in ("Resolved", "Closed", "Waiting for bug fix",
                          "Waiting for Feature", "Waiting for Customer"):
        return False
    return (issue.isActive() and assignee is None)

# -----------------------------------------------------------------------------
# TRIMMERS (trim issue with extra info into just what's needed to display it)
# -----------------------------------------------------------------------------


def trimmedSLAIssue(issue):
    """Trim an SLA issue to just it's id and the number of hours and minutes
    until it expires."""
    now = datetime.utcnow()
    started = issue.doc["sla"]["startAt"]
    expires = issue.doc["sla"]["expireAt"]
    if started != expires:
        percent_expired = (now - started).total_seconds() \
            / (expires - started).total_seconds() * 100
    else:
        percent_expired = 0
    percent_expired = min(percent_expired, 99.999)
    return {"id": issue.doc["jira"]["key"],
            "priority": issue.priority,
            "assignee": issue.assigneeDisplayName,
            "total_seconds": (expires-now).total_seconds(),
            "percentExpired": percent_expired}


def trimmedFTSIssue(issue):
    """Trim an FTS issue to just it's id and the number of hours and minutes
    since someone with a mongodb email commented publicly on it."""
    now = datetime.utcnow()
    allComments = issue.doc['jira']['fields']['comment']['comments']
    lastComment = issue.lastXGenPublicComment
    if lastComment is None:
        lastUpdate = issue.updated
    else:
        # Need when the issue was updated, not just created, so get all the
        # comment info
        lastUpdate = allComments[lastComment['cidx']]["updated"]
    mins = (now - lastUpdate).seconds / 60
    days = (now - lastUpdate).days
    return {"id": issue.doc["jira"]["key"],
            "priority": issue.priority,
            "assignee": issue.assigneeDisplayName,
            "days": days,
            "hours": mins / 60,
            "minutes": mins % 60}


def trimmedREVDoc(doc):
    """Trim a REV issue to just it's id and the number of hours and minutes
    since it was created. Note here the doc does not have all the JIRA fields,
    but lives in a separate reviews collection"""
    now = datetime.utcnow()
    lastUpdate = doc["requested_at"]
    mins = (now - lastUpdate).seconds / 60
    days = (now - lastUpdate).days
    eyes_on = doc["reviewers"]
    if 'lookers' in doc:
        eyes_on = doc['lookers'] + eyes_on
    return {"id": doc["key"],
            "days": days,
            "hours": mins / 60,
            "minutes": mins % 60,
            "requestedby": doc["requested_by"],
            "reviewers": eyes_on}


def trimmedUNAIssue(issue):
    """Trim a UNA issue to just it's id and the number of hours and minutes
    since the last public xgen comment (the last time we've paid attention to
    it)."""
    now = datetime.utcnow()
    allComments = issue.doc['jira']['fields']['comment']['comments']
    lastComment = issue.lastXGenPublicComment
    if lastComment is None:
        lastUpdate = issue.updated
    elif lastComment['cidx'] == len(allComments) - 1:  # It's the last comment
        # Need when the issue was updated, not just created, so get all the
        # comment info
        lastUpdate = allComments[lastComment['cidx']]["updated"]
    else:
        # There has been at least one comment since the public xgen
        # comment, so if there are any customer comments, base timing off the
        # first one.
        lastUpdate = allComments[lastComment['cidx']]["updated"]
        i = lastComment['cidx'] + 1
        while i < len(allComments):
            if not isMongoDBEmail(allComments[i]['author']['emailAddress']):
                # It's a customer
                lastUpdate = allComments[i]["updated"]
                break
            i += 1
    mins = (now - lastUpdate).seconds / 60
    days = (now - lastUpdate).days
    return {"id": issue.doc["jira"]["key"],
            "priority": issue.priority,
            "assignee": issue.assigneeDisplayName,
            "days": days,
            "hours": mins / 60,
            "minutes": mins % 60}


# -----------------------------------------------------------------------------
# OTHER HELPERS
# -----------------------------------------------------------------------------


def mergeAndSortIssues(dbd_issues, updated_issues):
    """Add the issues that were updated to the lists of issues on the
    dashboard and (re)sort them by priority. The priority will be the time, but
    which order we want them in depends on the type of issue."""

    def ascendingTimeOrder(t1, t2):
        """A custom comparator to order based on the difference in times in
        seconds. """
        return cmp(t1['total_seconds'], t2['total_seconds'])

    def descendingTimeOrder(t1, t2):
        """A custom comparator to order based on the hour and minute properties
        of the issues. Puts largest times first."""
        return -cmp((t1['days'], t1['hours'], t1['minutes']),
                    (t2['days'], t2['hours'], t2['minutes']))

    sorters = {
        "SLA": ascendingTimeOrder,
        "FTS": descendingTimeOrder,
        "REV": descendingTimeOrder,
        "UNA": descendingTimeOrder
    }

    for category in sorters:
        dbd_issues[category].extend(updated_issues[category])
        dbd_issues[category].sort(sorters[category])


def removeCompressedIssueIfPresent(issue, compressed_issues):
    """compressed_issues is a list of issues, but stripped down to just the
    information relevant to display them. Search through that list and remove
    the issue that has the same key as the one given, if one exists."""
    for i in compressed_issues:
        if i['id'] == issue.key:
            compressed_issues.remove(i)
            return


# -----------------------------------------------------------------------------
# LAUNCHING SERVER AS A DAEMON
# -----------------------------------------------------------------------------


if __name__ == "__main__":
    global args, logger
    desc = "Teledangos server for the TV version of the support dashboard."
    parser = argumentparserpp.CliArgumentParser(description=desc)
    parser.add_config_argument(
        "--pid", metavar="FILE", default="/tmp/teledangos.pid",
        help="specify a PID file (default=/tmp/teledangos.pid)"
    )
    parser.add_config_argument("--mongo-uri", metavar="MONGO",
                               default="mongodb://localhost:27017",
                               help="specify the MongoDB connection URI "
                                    "(default=mongodb://localhost:27017)")
    parser.add_config_argument(
        "--server-host", metavar="SERVER_HOST", default="localhost",
        help="specify the mongo hostname (default=localhost)"
    )
    parser.add_config_argument(
        "--server-port", metavar="SERVER_PORT", type=int, default=8080,
        help="specify the mongo port (default=8080)"
    )
    parser.add_argument(
        "command", choices=["start", "stop", "restart"],
        help="<-- the available actions, choose one"
    )
    args = parser.parse_args()
    pidfile = pidlockfile.PIDLockFile(args.pid)

    if args.command == "start":
        if pidfile.is_locked():
            print("There is already a running process")
            sys.exit(1)

    if args.command == "stop":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
            sys.exit(0)
        else:
            print("There is no running process to stop")
            sys.exit(2)

    if args.command == "restart":
        if pidfile.is_locked():
            pid = pidfile.read_pid()
            print("Stopping...")
            os.kill(pid, signal.SIGTERM)
        else:
            print("There is no running process to stop")

    # Require a log file and preserve it while daemonized
    if args.log is None:
        print("Please specify a log file")
        sys.exit(3)

    logger = logging.getLogger("logger")
    fh = logging.FileHandler(args.log)
    logger.setLevel(logging._levelNames[args.log_level])
    formatter = logging.Formatter('%(asctime)s - %(module)s - '
                                  '%(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # This is daemon territory
    teledangos_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
    context = daemon.DaemonContext(
        working_directory=teledangos_dir,
        pidfile=pidfile,
        stderr=fh.stream,
        stdout=fh.stream
    )
    context.files_preserve = [fh.stream]

    print("Starting...")

    with context:
        run(host=args.server_host, port=args.server_port)
    exit(0)
