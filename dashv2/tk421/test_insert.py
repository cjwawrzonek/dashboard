import argumentparserpp
import daemon
import logging
import os
import pidlockfile
import pymongo
import signal
import sys
import requests
import urllib2

from datetime import datetime, timedelta
from bottle import run, template, static_file, request, post, route
from bson.json_util import dumps
from supportissue import SupportIssue, isMongoDBEmail

# Timedelta has a new method in 2.7 that has to be hacked for 2.6
import ctypes as c

client = pymongo.MongoClient(host='localhost',port=24000)
support_db = client.support


issue = { "_id" : "test123ID",
	"ticket_id" : {
		"jira" : "211965"
	},
	"jira" : {
		"changelog" : {
			"total" : 1,
			"startAt" : 0,
			"histories" : [
				{
					"items" : [
						{
							"from" : "1",
							"to" : "1",
							"field" : "status",
							"fromStr" : "Open",
							"fieldtype" : "jira",
							"toStr" : "Open"
						},
						{
							"from" : "null",
							"to" : "13834",
							"field" : "Component",
							"fromStr" : "null",
							"fieldtype" : "jira",
							"toStr" : "Storage Engine - WiredTiger"
						},
						{
							"from" : "null",
							"to" : "angshuman.bagchi@10gen.com",
							"field" : "Owner",
							"fromStr" : "null",
							"fieldtype" : "custom",
							"toStr" : "Angshuman Bagchi"
						}
					],
					"created" : 'ISODate("2015-06-19T21:12:02Z")',
					"id" : "1219865",
					"author" : {
						"displayName" : "Angshuman Bagchi",
						"name" : "angshuman.bagchi@10gen.com",
						"self" : "https://jira.mongodb.org/rest/api/2/user?username=angshuman.bagchi%4010gen.com",
						"avatarUrls" : {
							"24x24" : "https://jira.mongodb.org/secure/useravatar?size=small&avatarId=10122",
							"32x32" : "https://jira.mongodb.org/secure/useravatar?size=medium&avatarId=10122",
							"48x48" : "https://jira.mongodb.org/secure/useravatar?avatarId=10122",
							"16x16" : "https://jira.mongodb.org/secure/useravatar?size=xsmall&avatarId=10122"
						},
						"emailAddress" : "angshuman.bagchi@10gen.com",
						"active" : "true"
					}
				}
			],
			"maxResults" : 1
		},
		"fields" : {
			"comment" : {
				"total" : 0,
				"startAt" : 0,
				"comments" : [ ],
				"maxResults" : 0
			},
			"customfield_10558" : "9223372036854775807",
			"customfield_10057" : "true",
			"creator" : {
				"displayName" : "Graham Frank",
				"name" : "jakiao",
				"self" : "https://jira.mongodb.org/rest/api/2/user?username=jakiao",
				"avatarUrls" : {
					"24x24" : "https://jira.mongodb.org/secure/useravatar?size=small&avatarId=10122",
					"32x32" : "https://jira.mongodb.org/secure/useravatar?size=medium&avatarId=10122",
					"48x48" : "https://jira.mongodb.org/secure/useravatar?avatarId=10122",
					"16x16" : "https://jira.mongodb.org/secure/useravatar?size=xsmall&avatarId=10122"
				},
				"emailAddress" : "graham@adsupply.com",
				"active" : "true"
			},
			"labels" : [ ],
			"customfield_11452" : "null",
			"customfield_11453" : "null",
			"watches" : {
				"self" : "https://jira.mongodb.org/rest/api/2/issue/CS-21942/watchers",
				"watchCount" : 1,
				"isWatching" : "false"
			},
			"customfield_11451" : "null",
			"customfield_10051" : [
				"jakiao(jakiao)"
			],
			"assignee" : "null",
			"lastViewed" : "null",
			"customfield_10052" : "839",
			"customfield_10055" : "null",
			"issuelinks" : [ ],
			"customfield_10056" : "angshuman.bagchi@10gen.com(angshuman.bagchi@10gen.com)",
			"customfield_11050" : "null",
			"customfield_11151" : "2015-06-19 20:59:14.0",
			"description" : "Hi there,\r\n\r\nWe run WiredTiger with directory per db set. Would it be possible to put certain DBs on alternate storage?\r\n\r\ni.e. we have a SSD array and a NVMe array on a machine; we place DBs 1-10 on SSD and DBs 11-15 on NVMe.\r\n\r\nThe default storage Mongo runs on is SSDs. To accomplish moving certain DBs to NVMe, could I move the DB folders to NVMe and then create a symbolic link in its place where Mongo expects the folder?\r\n\r\nAlso, if that is possible, could we prime a Mongo server before starting rsSync? I.e. on an empty data folder I create the symbolic links to NVMe storage and then start rsSync.\r\n\r\nDoes this make sense? Thanks.",
			"environment" : "null",
			"votes" : {
				"hasVoted" : "false",
				"self" : "https://jira.mongodb.org/rest/api/2/issue/CS-21942/votes",
				"votes" : 0
			},
			"priority" : {
				"iconUrl" : "https://jira.mongodb.org/images/icons/priorities/major.png",
				"self" : "https://jira.mongodb.org/rest/api/2/priority/3",
				"name" : "Major - P3",
				"id" : "3"
			},
			"attachment" : [ ],
			"customfield_10050" : "0.0",
			"duedate" : "null",
			"customfield_10857" : "null",
			"status" : {
				"statusCategory" : {
					"name" : "New",
					"self" : "https://jira.mongodb.org/rest/api/2/statuscategory/2",
					"id" : 2,
					"key" : "new",
					"colorName" : "blue-gray"
				},
				"description" : "The issue is open and ready for the assignee to start work on it.",
				"self" : "https://jira.mongodb.org/rest/api/2/status/1",
				"iconUrl" : "https://jira.mongodb.org/images/icons/statuses/open.png",
				"id" : "1",
				"name" : "Open"
			},
			"customfield_10559" : "null",
			"updated" : 'ISODate("2015-06-19T21:12:02Z")',
			"subtasks" : [ ],
			"customfield_12550" : "0|i0wcg7:",
			"reporter" : {
				"displayName" : "Graham Frank",
				"name" : "jakiao",
				"self" : "https://jira.mongodb.org/rest/api/2/user?username=jakiao",
				"avatarUrls" : {
					"24x24" : "https://jira.mongodb.org/secure/useravatar?size=small&avatarId=10122",
					"32x32" : "https://jira.mongodb.org/secure/useravatar?size=medium&avatarId=10122",
					"48x48" : "https://jira.mongodb.org/secure/useravatar?avatarId=10122",
					"16x16" : "https://jira.mongodb.org/secure/useravatar?size=xsmall&avatarId=10122"
				},
				"emailAddress" : "graham@adsupply.com",
				"active" : "true"
			},
			"customfield_10550" : "null",
			"customfield_10551" : "null",
			"customfield_10552" : "null",
			"customfield_10553" : "null",
			"customfield_10554" : "null",
			"customfield_10557" : "null",
			"customfield_10041" : {
				"displayName" : "Angshuman Bagchi",
				"name" : "angshuman.bagchi@10gen.com",
				"self" : "https://jira.mongodb.org/rest/api/2/user?username=angshuman.bagchi%\\4010gen.com",
				"avatarUrls" : {
					"24x24" : "https://jira.mongodb.org/secure/useravatar?size=small&avatarId=10122",
					"32x32" : "https://jira.mongodb.org/secure/useravatar?size=medium&avatarId=10122",
					"48x48" : "https://jira.mongodb.org/secure/useravatar?avatarId=10122",
					"16x16" : "https://jira.mongodb.org/secure/useravatar?size=xsmall&avatarId=10122"
				},
				"emailAddress" : "angshuman.bagchi@10gen.com",
				"active" : "true"
			},
			"customfield_11450" : "null",
			"customfield_10031" : "null",
			"customfield_10030" : {
				"self" : "https://jira.mongodb.org/rest/api/2/group?groupname=Adsupply",
				"name" : "Adsupply"
			},
			"created" : 'ISODate("2015-06-19T20:59:14Z")',
			"versions" : [ ],
			"resolutiondate" : "null",
			"customfield_10053" : "null",
			"summary" : "Mongo3.0 + WiredTiger + Storage Space",
			"project" : {
				"name" : "Commercial Support",
				"self" : "https://jira.mongodb.org/rest/api/2/project/10021",
				"avatarUrls" : {
					"24x24" : "https://jira.mongodb.org/secure/projectavatar?size=small&pid=10021&avatarId=10011",
					"32x32" : "https://jira.mongodb.org/secure/projectavatar?size=medium&pid=10021&avatarId=10011",
					"48x48" : "https://jira.mongodb.org/secure/projectavatar?pid=10021&avatarId=10011",
					"16x16" : "https://jira.mongodb.org/secure/projectavatar?size=xsmall&pid=10021&avatarId=10011"
				},
				"projectCategory" : {
					"self" : "https://jira.mongodb.org/rest/api/2/projectCategory/10003",
					"id" : "10003",
					"name" : "Support",
					"description" : ""
				},
				"key" : "CS",
				"id" : "10021"
			},
			"components" : [
				{
					"self" : "https://jira.mongodb.org/rest/api/2/component/13834",
					"description" : "Issues related to the WiredTiger storage engine",
					"id" : "13834",
					"name" : "Storage Engine - WiredTiger"
				}
			],
			"customfield_12551" : [ ],
			"issuetype" : {
				"name" : "Question",
				"self" : "https://jira.mongodb.org/rest/api/2/issuetype/6",
				"iconUrl" : "https://jira.mongodb.org/images/icons/issuetypes/undefined.png",
				"subtask" : "false",
				"id" : "6",
				"description" : ""
			},
			"resolution" : "null",
			"workratio" : -1
		},
		"self" : "https://jira.mongodb.org/rest/api/2/issue/211965",
		"key" : "CS-21942",
		"id" : "211965",
		"expand" : "operations,editmeta,changelog,transitions,renderedFields"
	},
	"dash" : {
		"active" : {
			"now" : "true",
			"ever" : "true"
		},
		"firstXGenPublicCommentAfterCustomerComment" : "null",
		"earliestOfLastCustomerComments" : "null",
		"tse" : {
			"supported" : {
				"now" : "true",
				"ever" : "true"
			}
		},
		"lastXGenOnlyComment" : "null",
		"lastXGenPublicComment" : "null",
		"firstCustomerComment" : "null",
		"lastCustomerComment" : "null",
		"firstXGenPublicComment" : "null"
	},
	"deleted" : "false",
	"updated" : 'ISODate("2015-06-19T21:13:14.658Z")',
	"sla" : {
		"inputs" : {
			"priority" : 3,
			"project" : "CS",
			"group" : "Adsupply",
			"components" : [
				"Storage Engine - WiredTiger"
			],
			"contract" : "prod-support"
		},
		"startAt" : 'ISODate("2015-06-19T20:59:14Z")',
		"missed" : "false",
		"expireAt" : 'ISODate("2015-06-20T04:59:14Z")',
		"totalMinutes" : 480,
		"satisfiedAt" : "null"
	}
}
# print type(support_db.issues)
# print support_db.issues.find_one()
# post = {"author": "Mike",
# 		"text": "My first blog post!",
#        	"tags": ["mongodb", "python", "pymongo"]
#        	}

# issue = ''.join(issue.split())

proj = {"_id":1,"sla":1,"missed":0}
# proj = dumps(proj)
# print proj
# exit()
# proj = ''.join(dumps(proj).split())

query = {"_id":1234,"sla":{"$exists":True},"missed":0}
# issue = ''.join(dumps(query).split())
# issue = dumps(query)

col = "issues"

payload = {'col':col,'query':issue,'proj':proj}

r = requests.get("http://localhost:8080/col/query/proj/", params=payload)
# print issue
print r.url

exit()
collection = support_db.issues
# print collection.count()
# # exit()

# result = collection.insert(issue)
result = collection.remove(issue)
print collection.count()

print result




