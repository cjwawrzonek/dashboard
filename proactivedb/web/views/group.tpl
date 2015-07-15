<%
import datetime

def getTimestamp(objectId):
    tmp = objectId.__str__()
    tmp = tmp[:8]
    return int(tmp, 16)
end

def getDatetime(objectId):
    n = getTimestamp(objectId)
    return datetime.datetime.fromtimestamp(n)
end

def getNTests(type):
    n = 0

    src = None
    if type == 'failed' or type == 'ticketed':
        src = group['failedtests']
    elif type == 'resolved':
        src = group['resolvedTests']
        else:
        return n
    end

    for test in src:
        ticketed = test.get('ticket')
        if type == 'ticketed' and ticketed is None:
            continue
        end
        resolved = test.get('resolved')
        if type == 'resolved' and resolved is None:
            continue
        end
        if type == 'failed' and (ticketed is not None or resolved is not None):
            continue
        end
        n += 1
    end
    return n
end

def showTests(type):
    src = None
    if type == 'failed' or type == 'ticketed':
        src = group['failedtests']
    elif type == 'resolved':
        src = group['resolvedTests']
    end

    for test in src:
        ticketed = test.get('ticket')
        if type == 'ticketed' and ticketed is None:
            continue
        end
        resolved = test.get('resolved')
        if type == 'resolved' and resolved is None:
            continue
        end
        if type == 'failed' and (ticketed is not None or resolved is not None):
            continue
        end

        testName = test['test']
        testSrc = test['src']
        testComment = ""
        testHeader = ""
        if type != 'resolved' and testSrc in testDescriptionCache and testName in testDescriptionCache[testSrc] and 'comment' in testDescriptionCache[testSrc][testName]:
            testComment = testDescriptionCache[testSrc][testName]['comment']
            testHeader = testDescriptionCache[testSrc][testName]['header']
        end
        testId = test.get('ftid')
        if testId is None:
            testId = test.get('_id')
        end
        failedTs = getDatetime(testId)
        testIgnore = test.get('ignore', None)
        testNids = test['nids']

        # A ticket already exists for this test
        testClass = ""
        if ticketed is not None:
            ticketKey = ticketed.get('key')
            ticketTs = ticketed.get('ts').replace(microsecond=0)
            testClass = "alert-warning"
        end
        if resolved is not None:
            testClass = "alert-success"
        end
%>
<div id="div_failedtests_{{testId}}" class="alert {{testClass}}">
<%
        nfailedSpan = "%s" % testNids
%>
    <span id="div_failedtests_{{testId}}_title" class="h4">{{!testName}} <a data-toggle="collapse" href="#collapse{{testId}}" aria-expanded="false" aria-controls="collapse{{testId}}" class="link link-danger">
    <span class="label label-danger">{{!nfailedSpan}}</span></a></span>
    <span class="pull-right"><a href="#">+</a> <a href="#">x</a></span><br/><br/>
    <div style="display:none">
%       if type != 'resolved':
        <div class="header editable">{{!testHeader}}</div>
        <div class="comment editable">{{!testComment}}</div>
%       end
    </div>
    <div class="collapse" id="collapse{{testId}}">
        <div class="well">
<%
        ids = test['ids']
        for _id in ids:
            if _id.__str__() in group['ids']:
                ping = group['ids'][_id.__str__()]
                gid = ping.get('gid')
                hid = ping.get('hid')
                doc = ping.get('doc')
                if doc is not None:
                    host = doc.get('host')
                    port = doc.get('port')
                else:
                    host = "null"
                    port = "null"
                end
%>
            <a href="https://mms.mongodb.com/host/detail/{{gid}}/{{hid}}">{{host}}:{{port}}</a></br>
<%          end
        end
%>
        </div>
    </div>
        {{failedTs}}: Last noticed<br/>
%       if ticketed is not None:
        {{ticketTs}}: Created <a href="https://jira.mongodb.org/browse/{{ticketKey}}">{{ticketKey}}</a><br/>
%       end
%       if resolved is not None:
        {{resolved.replace(microsecond=0)}}: Issue resolved
%       end
<%
        if type == "resolved":
            pass
        else:
%>
    <br/>
    <div role="group" aria-label="buttons">
        <button type="button" class="btn btn-danger">Ignore forever</button>
        <button type="button" class="btn btn-primary" onclick="addToTicket(this, '{{!testId}}')">Add to ticket</button>
    </div>
%       end
</div>
    <%
    end
end
%>

<div class="container-fluid">
    <div class="row">
        <div class="col-lg-6">
            <h1>{{group['name']}}</h1>

%   if 'mms' in group:
        <strong>MMS:</strong>
%       for mms in group['mms']:
            <a href="https://mms.mongodb.com/host/list/{{mms['id']}}">{{mms['name']}}</a> 
%       end
        <br/>
<%
    end
jira_groups = []
if group['company'] is not None:
    if 'sales' in group['company'] and group['company']['sales'] is not None and len(group['company']['sales']) > 0:
        salesrep = group['company']['sales'][0]['jira']
    else:
        salesrep = None
    end

    sf_account_id = group['company'].get('sf_account_id')
    sf_project_id = group['company'].get('sf_project_id')
    jira_groups = group['company'].get('jira_groups', [])
%>
            <strong>Salesforce:</strong> <a href="https://mongodb.my.salesforce.com/{{sf_account_id}}">Account</a>,
            <a href="https://mongodb.my.salesforce.com/{{sf_project_id}}">Project</a>
            &nbsp;<strong>Sales Rep:</strong> <a href="https://corp.10gen.com/employees/{{salesrep}}">{{salesrep}}</a>
            <input id="gid" type="hidden" value="{{group['_id']}}">
            <br/>
            <strong>Support Expiration: </strong>
            % if 'support_expiration_date' in group['company']:
            %     if group['company']['support_expiration_date'] < datetime.datetime.today():
                <span style="color:red">
            %     end
                {{group['company']['support_expiration_date']}}
            %     if group['company']['support_expiration_date'] < datetime.datetime.today():
                </span>
            %     end
            % end
% else:
            <strong>This may not be a CS Customer</strong>
% end
            <br/>
<%
    jqlCompanyString = 'company%20in%20('
    for i in range(0, len(jira_groups)):
        jqlCompanyString += '"%s"' % jira_groups[i]
        if i < (len(jira_groups)-1):
            jqlCompanyString += ','
        end
    end
    jqlCompanyString += ')'
%>
            <a target="_blank" href="https://jira.mongodb.org/issues/?jql=project%20%3D%20%22Commercial%20Support%22%20AND%20{{jqlCompanyString}}">Existing Support Tickets</a>
        </div>
    </div>
    <hr/>
    <div class="row">
        <div class="col-lg-6" style="overflow: hidden;">
            <div>
                <h4>Customer Notes</h4> <a href="javascript:addNoteToGroup();" id="a_addNoteToGroup"><span class="glyphicon glyphicon-plus"/></a>
                <div id="div_notes">
    <%
    if 'notes' in group:
        notes = group['notes']
        print(notes)
        for i in range(0, len(notes)):
            note = notes[i]
            print(note)
    %>
                    <div class="div_note" id="{{note['sfid']}}">
                        {{note['author']}}@{{datetime.datetime.fromtimestamp(note['createdDateTS']).isoformat()}}: <span class="editable">{{note['text']}}</span> <a href="javascript:deleteNote('{{note['sfid']}}')">X</a>
                    </div>
    <%
        end
    end
    %>
                </div>
            </div>
            <div style="clear:both"></div>
            <br/>
            <div>
                <span class="h4">Proactive Ticket Draft</span>
                <select style="float:right" id="jira_group">
%   for jg in jira_groups:
                    <option value="{{jg}}">{{jg}}</option>
%   end
                </select>
            </div><br>
            <div id="div_ticket" class="well well-sm">
                <h4>Summary:</h4>
                <div id="div_ticketSummary">
                    <div class="editable">
                        MongoDB Proactive: Issues identified in MMS
                    </div>
                </div>
                <h4>Description:</h4>
                <div id="div_ticketDescription">
                    <div class="editable">
                        {{testDescriptionCache.get('greeting')}},
                    </div><br/>
                    <div class="editable">
                        {{testDescriptionCache.get('opening')}}
                    </div><br/>
                    <div id="div_ticketDescription_mainBody"></div>
                    <div class="editable">
                        {{!testDescriptionCache.get('closing')}}
                    </div><br/>
                    <div class="editable">
                        {{!testDescriptionCache.get('signoff')}}
                    </div>
                </div>
            </div>
            <div class="pull-right">
                <a class="btn btn-warning" id="a_previewTicket" href="javascript:void(0);">Preview Ticket</a>
                <a class="btn btn-primary" id="a_createTicket" href="javascript:void(0);">Create Ticket</a>
            </div>
        </div>
        <div class="col-lg-6">
            <span class="h4 pull-right">Failed Tests</span>
            <ul id="myTab" class="nav nav-tabs" role="tablist">
                <li role="presentation" class="active"><a href="#failed" id="failed-tab" role="tab" data-toggle="tab" aria-controls="failed" aria-expanded="true">Not Ticketed ({{getNTests('failed')}})</a></li>
                <li role="presentation"><a href="#ticketed" id="ticketed-tab" role="tab" data-toggle="tab" aria-controls="ticketed" aria-expanded="true">Ticketed ({{getNTests('ticketed')}})</a></li>
                <li role="presentation"><a href="#resolved" id="resolved-tab" role="tab" data-toggle="tab" aria-controls="resolved" aria-expanded="true">Gone away ({{getNTests('resolved')}})</a></li>
            </ul><br/>
            <div class="tab-content">
                <div role="tabpanel" class="tab-pane active" id="failed" aria-labelledBy="failed-tab">
%                   showTests('failed')
                </div>
                <div role="tabpanel" class="tab-pane" id="ticketed" aria-labelledBy="ticketed-tab">
%                   showTests('ticketed')
                </div>
                <div role="tabpanel" class="tab-pane" id="resolved" aria-labelledBy="resolved-tab">
%                   showTests('resolved')
                </div>
            </div>
        </div>
    </div>
    <div class="modal fade" id="previewModal" tabindex="-1" role="dialog" aria-hidden="true">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    <span class="h4 modal-title" id="myModalLabel">Ticket Preview</span> <span id="active_jira_group"></span>
                </div>
                <div class="modal-body">
                    <pre id="ticketPreview"></pre>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-default" data-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>
</div>
