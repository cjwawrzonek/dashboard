var workflowsObj = {};
var workflows = [];

/**
 * Generates an onclick function to render a test.
 * @return {function} function to be executed onclick
 */
function renderClick() {
    return function(e){ renderWorkflow(e.data); };
}

/**
 * Generates an onclick function to remove a test.
 * @return {function} function to be executed onclick
 */
function renderRemoveClick() {
    return function (e) {
        removeWorkflow(e.data);
    };
}

function renderList(workflows) {
    var list = $('#existingflows');
    list.empty();
    for(var wf = 0; wf < workflows.length; wf++){
        var workflow = workflows[wf];
        var el = $('<li></li>');
        var item = $('<a href="javascript:void(0);" class="col-xs-9">' + workflow.name + '</a>');
        var removelink = $('<a href="javascript:void(0);" class="text-danger col-xs-1"><i class="glyphicon glyphicon-trash" data-toggle="tooltip" data-placement="top" title="Remove Workflow"></i></a>');
        removelink.find('i').tooltip();
        removelink.click(workflow.name,renderRemoveClick());
        item.click(wf,renderClick());
        item.appendTo(el);
        removelink.appendTo(el);
        el.appendTo(list);
    }
}

function getWorkflowList(){
    $.ajax({
        type: "GET",
        url: "/workflow",
        datatype: "json"
    }).success(function(response){
        workflows = [];
        workflowsObj = JSON.parse(response);
        for (var wf = 0; wf < workflowsObj.data.workflows.length; wf++) {
            var wfObj;
            wfObj = workflowsObj.data.workflows[wf];
            workflows[wf] = wfObj;
        }
        renderList(workflows);
    });
}

function renderWorkflow(wfid) {
    clearForm();
    var workflow = workflows[wfid];
    $(":input[id='workflow.name']").val(workflow.name);
    $(":input[id='workflow.desc']").val(workflow.desc);
    $(":input[id='workflow._id']").val(workflow._id.$oid);
    $(":input[id='workflow.owner']").val(workflow.owner);
    $(":input[id='workflow.groups']").val(workflow.groups);
    renderPrereqs(workflow.prereqs);
    $(":input[id='workflow.ns']").val(workflow.ns);
    $(":input[id='workflow.join_key']").val(workflow.join_key);
    // convert templated variables to something JSON.parse can parse
    workflow.query_string = workflow.query_string.replace(/\[\[([0-9A-Z_]+)\]\]/, '"%5B%5B$1%5D%5D"');
    workflow.query_string = JSON.stringify(JSON.parse(workflow.query_string), null, 4);
    // convert back
    workflow.query_string = workflow.query_string.replace(/"%5B%5B([0-9A-Z_]+)%5D%5D"/, '[[$1]]');
    $(":input[id='workflow.query_string']").val(workflow.query_string);
    $(":input[id='workflow.ns1']").val(workflow.ns1);
    $(":input[id='workflow.join_key1']").val(workflow.join_key1);
    if (typeof workflow.query_string1 !== "undefined") {
        // convert templated variables to something JSON.parse can parse
        workflow.query_string1 = workflow.query_string1.replace(/\[\[([0-9A-Z_]+)\]\]/, '"%5B%5B$1%5D%5D"');
        workflow.query_string1 = JSON.stringify(JSON.parse(workflow.query_string1), null, 4);
        // convert back
        workflow.query_string1 = workflow.query_string1.replace(/"%5B%5B([0-9A-Z_]+)%5D%5D"/, '[[$1]]');
        $(":input[id='workflow.query_string1']").val(workflow.query_string1);
    }
    if (workflow.auto_approve === true) {
        $(":input[id='workflow.auto_approve']").prop('checked', true);
        $(":input[id='workflow.auto_approve']").val('true')
    } else {
        $(":input[id='workflow.auto_approve']").prop('checked', false);
        $(":input[id='workflow.auto_approve']").val('true');
    }
    // set auto-approve to read-only for non-admins
    // note to hackers: i check on the other side too so don't bother
    groups = $.cookie('groups').replace(/\\054/g,',');
    if ($.inArray("admin", JSON.parse(groups)) < 0) {
        $(":input[id='workflow.auto_approve']").attr('disabled', 'disabled');
    }
    if (workflow.public === true) {
        $(":input[id='workflow.public']").prop('checked', true);
        $(":input[id='workflow.public']").val('true')
    } else {
        $(":input[id='workflow.public']").prop('checked', false);
        $(":input[id='workflow.public']").val('true')
    }
    renderActions(workflow.actions);
}

function removeWorkflow(wfname){
    if(confirm("Are you sure you want to delete workflow " + wfname + "?")){
        clearForm();
        $.ajax({
            type: "DELETE",
            url: "/workflow/" + wfname,
            datatype: "json"
        }).success(function(){
            console.log("Deleted " + wfname);
            getWorkflowList();
        });
    } else {
        return false;
    }
}

function clearForm(){
    $(':input').val("");
    $("#prereqsList").empty().append(renderAddPrereq());
    $("#actionsList").empty().append(renderAddAction());
    $("#test-workflow-form").hide();
}

function renderActions(actions) {
    var parent = $('#actionsList');
    parent.empty();
    if(actions !== undefined) {
        for (var action = 0; action < actions.length; action++) {
            var root = renderAction(actions[action], action);
            root.appendTo(parent);
        }
    }
    var addaction = renderAddAction();
    addaction.appendTo(parent);
}

function renderAction(action,index){
    var root = $('<tr id="action-' + index + '" class="action"></tr>');
    var namenode = renderActionName(action, index);
    var argsnode = renderActionArgs(action, index);
    namenode.appendTo(root);
    argsnode.appendTo(root);
    return root;
}

function renderActionName(action, index){
    var root = $('<td class="col-sm-3"></td>');
    var nameinput = $('<input id="workflow.actions[' + index +'].name" name="workflow.actions[' + index +'].name" class="form-control input-sm"/>');
    if(action && action.name){
        nameinput.val(action.name);
    }
    var removelink = $('<a href="javascript:void(0);" class="text-danger remove-row" data-toggle="tooltip" data-placement="top" title="Remove Action"><i class="glyphicon glyphicon-trash"></i></a>')
        .tooltip()
        .hover(
            function(){
                $(this).closest('tr').addClass('bg-danger');
            },
            function(){
                $(this).closest('tr').removeClass('bg-danger');
            }
        );
    removelink.on('click',function(){removeAction($(this).closest('tr'));});
    nameinput.appendTo(root);
    $('<br/>').appendTo(root);
    removelink.appendTo(root);
    return root;
}

function renderActionArgs(action,index){
    var root = $('<td id="action-"' + index + '-args" class="col-sm-9">');
    if(action && action.args) {
        for (var arg = 0; arg < action.args.length; arg++) {
            var arginput = actionArgHtml(index,arg);
            arginput.find('textarea').val(action.args[arg]);
            arginput.appendTo(root);
        }
    }
    var addarg = renderAddActionArg(index);
    addarg.appendTo(root);
    return root;
}

function actionArgHtml(actionindex,argindex){
    /*jshint multistr: true */
    var content = '<div class="form-group"> \
                <div class="col-sm-11"> \
                    <textarea id="workflow.actions[' + actionindex + '].args[' + argindex + ']" name="workflow.actions[' + actionindex + '].args[' + argindex + ']" class="form-control input-sm" rows="10"></textarea> \
                </div> \
                <div class="col-sm-1"> \
                    <a href="javascript:void(0);" class="pull-right text-danger remove-argument-link"><i class="glyphicon glyphicon-trash" data-toggle="tooltip" data-placement="top" title="Remove Argument"></i></a> \
                </div> \
            </div>';
    var root = $(content);
    root.find('.remove-argument-link i').tooltip();
    root.find('.remove-argument-link')
        .click(function(){removeActionArg($(this).parent().parent());})
        .tooltip()
        .hover(function(){$(this).closest('td').addClass('bg-danger');},function(){$(this).closest('td').removeClass('bg-danger');});
    return root;
}

function renderPrereqs(prereqs) {
    var parent = $('#prereqsList');
    parent.empty();
    if(prereqs !== undefined) {
        for (var prereq = 0; prereq < prereqs.length; prereqs++) {
            var root = renderPrereq(prereqs, prereq);
            root.appendTo(parent);
        }
    }
    var addprereq = renderAddPrereq();
    addprereq.appendTo(parent);
}


function renderPrereq(prereqs,index){
    var prereq = null;
    if(prereqs && prereqs[index]){
        prereq = prereqs[index];
    }
    var root = $('<tr id="prereq-' + index + '" class="prereq"></tr>');
    var col1 = $('<td class="col-sm-1"></td>');
    var col2 = $('<td class="col-sm-6"></td>');
    var col3 = $('<td class="col-sm-5"></td>');
    var content2 = $('<select id="workflow.prereqs[' + index +'].name" name="workflow.prereqs[' + index +'].name" class="form-control input-sm"></select');
    var content3 = $('<input id="workflow.prereqs[' + index +'].time_elapsed" name="workflow.prereqs[' + index +'].time_elapsed" class="form-control input-sm"/>');
    var removelink = $('<a href="javascript:void(0);" class="text-danger remove-row"><i class="glyphicon glyphicon-trash" data-toggle="tooltip" data-placement="top" title="Remove Prerequisite"></i></a>');
    removelink.find('i').tooltip();
    removelink.click(function(){removePrereq($(this).parent().parent());})
        .tooltip()
        .hover(function(){$(this).closest('tr').addClass('bg-danger');},function(){$(this).closest('tr').removeClass('bg-danger');});

    $('<option></option>').val("").appendTo(content2);
    for (var wf = 0; wf < workflows.length; wf++) {
        $('<option></option>').text(workflows[wf].name).val(workflows[wf].name).appendTo(content2);
    }
    if(prereq && prereq.name){
        content2.val(prereq.name);
    }
    if(prereq && prereq.time_elapsed){
        content3.val(prereq.time_elapsed);
    }
    removelink.appendTo(col1);
    content2.appendTo(col2);
    content3.appendTo(col3);
    col1.appendTo(root);
    col2.appendTo(root);
    col3.appendTo(root);
    return root;
}

function renderAddAction(){
    var root = $('<tr id="addAction-link"></tr>');
    var col = $('<td colspan="2"></td>');
    var link = $('<a href="javascript:void(0);"><i class="glyphicon glyphicon-plus" data-toggle="tooltip" data-placement="top" title="Add Action"></i></a>');
    link.find('i').tooltip();
    link.hover(
        function(){$(this).closest('tr').addClass('bg-success');},
        function(){$(this).closest('tr').removeClass('bg-success');}
    );
    link.click(function(){addAction();});
    link.appendTo(col);
    col.appendTo(root);
    return root;
}

function renderAddActionArg(actionindex){
    var root = $('<div id="addActionArg-' + actionindex + '-link" class="pull-right"></div>');
    var link = $('<a href="javascript:void(0);"><i class="glyphicon glyphicon-plus" data-toggle="tooltip" data-placement="top" title="Add Argument"></i></a>');
    link.find('i').tooltip();
    link.hover(
        function(){$(this).closest('td').addClass('bg-success');},
        function(){$(this).closest('td').removeClass('bg-success');}
    );
    link.click(function(){addActionArg(actionindex);});
    link.appendTo(root);
    return root;
}

function renderAddPrereq(){
    var root = $('<tr id="addPrereq-link"></tr>');
    var col = $('<td colspan="3"></td>');
    var link = $('<a href="javascript:void(0);"><i class="glyphicon glyphicon-plus" data-toggle="tooltip" data-placement="top" title="Add Prerequisite"></i></a>');
    link.find('i').tooltip();
    link.tooltip().hover(
        function(){$(this).closest('tr').addClass('bg-success');},
        function(){$(this).closest('tr').removeClass('bg-success');}
    );
    link.click(function(){addPrereq();});
    link.appendTo(col);
    col.appendTo(root);
    return root;
}

function removeAction(parent){
    $(parent).remove();
}

function removeActionArg(parent) {
    $(parent).remove();
}

function removePrereq(parent){
    $(parent).remove();
}

function addAction(){
    var link = $('#addAction-link');
    var container = link.parent();
    var argindex = container.children().length - 1;
    var content = renderAction(null,argindex);
    if(argindex === 0){
        container.prepend(content);
    } else {
        link.prev().after(content);
    }
}

function addActionArg(actionindex){
    var link = $('#addActionArg-' + actionindex + '-link');
    var container = link.parent();
    var argindex = container.children().length - 1;
    var content = actionArgHtml(actionindex,argindex);
    if(argindex === 0){
        container.prepend(content);
    } else {
        link.prev().after(content);
    }
}

function addPrereq(){
    var link = $('#addPrereq-link');
    var container = link.parent();
    var argindex = container.children().length - 1;
    var content = renderPrereq(null);
    if(argindex === 0){
        container.prepend(content);
    } else {
        link.prev().after(content);
    }
}

function saveChanges(form) {
    var saveCallback = function() {
        var formid = $(form).attr('id');
        var jsonform = form2js(document.getElementById(formid), ".", true, undefined, true, true);
        // groups is an array
        if ('groups' in jsonform['workflow']) {
            groups = jsonform['workflow']['groups'].split(',');
        } else {
            groups = [];
        }
        jsonform['workflow']['groups'] = groups
        var formdata = JSON.stringify(jsonform, null, 4);
        var url = "/workflow/" + jsonform.workflow.name;
        var exists = false;
        for (var wf = 0; wf < workflows.length; wf++) {
            if (workflows[wf].name == jsonform.workflow.name && workflows[wf]._id.$oid != jsonform.workflow._id) {
                exists = true;
            }
        }
        if (exists) {
            alert("A workflow named " + jsonform.workflow.name+ " already exists. Changes have not been saved.");
            return false;
        } else {
            saveWorkflow(formdata, url);
        }
    };
    return testWorkflow(saveCallback);
}

function saveChangesNew(form) {
    var saveCallback = function() {
        var formid = $(form).attr('id');
        var jsonform = form2js(document.getElementById(formid), ".", true, undefined, true, true);
        delete jsonform.workflow._id;
        // groups is an array
        if ('groups' in jsonform['workflow']) {
            groups = jsonform['workflow']['groups'].split(',');
        } else {
            groups = [];
        }
        jsonform['workflow']['groups'] = groups

        var formdata = JSON.stringify(jsonform, null, 4);
        var url = "/workflow";
        var exists = false;
        for (var wf = 0; wf < workflows.length; wf++) {
            if (workflows[wf].name == jsonform.workflow.name) {
                exists = true;
            }
        }
        if (exists) {
            alert("A workflow named " + jsonform.workflow.name + " already exists. Changes have not been saved.");
            return false;
        } else {
            saveWorkflow(formdata, url);
        }
    };
    return testWorkflow(saveCallback);
}

function saveWorkflow(content,url){
    var lsave = Ladda.create(document.querySelector('#save-link'));
	lsave.start();
    $.ajax({
        type : "POST",
        url : url,
        data : content
    }).success(function(){
        getWorkflowList();
        clearForm();
    }).error(function(e){
        alert("Workflow was NOT saved for the following reason:\n" + e.status + " : " + e.statusText );
        console.log(e);
    }).always(function(){
        lsave.stop();
    });
}

function testWorkflow(callback){
    var summary = $('#test-workflow-summary');
    var results = $('#test-workflow-results');
    summary.empty();
    results.empty();
    var jsonform = form2js(document.getElementById('workflow-form'),".",true,undefined,true,true);
    var formdata = JSON.stringify(jsonform,null,4);
    var url = "/testworkflow";
    var l = Ladda.create(document.querySelector('#test-workflow-link'));
	l.start();
    $.ajax({
        type : "POST",
        url : url,
        data : formdata,
        datatype : "json",
        async: true
    }).success(function(response){
        var responseObj = JSON.parse(response);
        renderTestSummary(responseObj, summary);
        if(responseObj.status == "success") {
            renderResults(responseObj.data, results);
        }
        $('#test-workflow-form').show();
        if(responseObj.status == "success") {
            if(typeof callback === "function") {
                callback();
            }
            return true;
        } else {
            return false;
        }
    }).error(function(e){
        console.log(e);
        return false;
    }).always(function(){
        l.stop();
    });
}

function renderResults(results,container){
    ns = results['ns'];
    docs = results['docs'];
    if (ns == "support.issues") {
        content='<table class="table table-striped"><thead><tr><th>Ticket</th><th>Workflows Performed</th><th>Status</th></tr></thead><tbody id="test-workflow-results">';
    }
 
    for(var i=0; i < docs.length; i++){
        var doc = docs[i];
        var workflows = [];
        if(doc !== undefined && doc.karakuri !== undefined && doc.karakuri.workflows_performed !== undefined) {
            for (var wf = 0; wf < doc.karakuri.workflows_performed.length; wf++) {
                workflows.push(doc.karakuri.workflows_performed[wf].name);
            }
        }
        var performed = workflows.join(", ");
        if (ns == "support.issues") {
                content += '<tr>' +
                '<td><a target="_blank" href="https://jira.mongodb.com/browse/' + doc.jira.key + '">' + doc.jira.key + '</a></td>' +
                '<td>' + performed + '</td>' +
                '<td>' + doc.jira.fields.status.name + '</td>' +
                '</tr>';
        } else {
            console.log(JSON.stringify(doc));
            $("<pre style='float:left;margin:1em;white-space:pre-wrap;'>"+JSON.stringify(doc, null, 4)+"</pre>").appendTo(container);
        }
    }

    if (ns == "support.issues") {
        content += '</tbody></table>';
        $(content).appendTo(container);
    }
}

function renderTestSummary(response,container){
    var statusColor = "success";
    var messageText = "All tests passed successfully!";
    if(response.status == "error") {
        statusColor = "danger";
        messageText = response.message;
    }
    $('<div class="alert alert-' + statusColor + '">' + messageText + '</div>').appendTo(container);
}

$(document).ready(function() {
    getWorkflowList();
    $('#create-btn').click(function(){clearForm();});
    $('#add-action-btn').click(function(){addAction();})
        .tooltip()
        .hover(
            function(){$(this).closest('tr').addClass('bg-success');},
            function(){$(this).closest('tr').removeClass('bg-success');}
    );
    $('#add-prereq-btn').click(function(){addPrereq();})
        .tooltip()
        .hover(
            function(){$(this).closest('tr').addClass('bg-success');},
            function(){$(this).closest('tr').removeClass('bg-success');}
    );
    $('#save-link').click(function(){saveChanges($(this).closest('form'));});
    $('#save-copy-link').click(function(){saveChangesNew($(this).closest('form'));});
    $('#test-workflow-link').click(function(){testWorkflow();});
    $('#test-workflow-close').click(function(){$('#test-workflow-form').hide();});
});