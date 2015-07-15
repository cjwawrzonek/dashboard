var gRefreshDelay = 15;
var gRefreshWarningDelay = 30;
var gData = {};

var gRows = ['SLA', 'FTS', 'REV', 'UNA'];

// A loading spinner to show when it's refreshing.
var opts = {
  lines: 8, // The number of lines to draw
  length: 4, // The length of each line
  width: 2, // The line thickness
  radius: 5, // The radius of the inner circle
  corners: 1, // Corner roundness (0..1)
  rotate: 0, // The rotation offset
  direction: 1, // 1: clockwise, -1: counterclockwise
  color: '#000', // #rgb or #rrggbb or array of colors
  speed: 1.7, // Rounds per second
  trail: 60, // Afterglow percentage
  shadow: false, // Whether to render a shadow
  hwaccel: false, // Whether to use hardware acceleration
  className: 'spinner', // The CSS class to assign to the spinner
  zIndex: 2e9, // The z-index (defaults to 2000000000)
  top: '50%', // Top position relative to parent
  left: '50%' // Left position relative to parent
};
var gSpinTarget = document.getElementById('next-update');
var gSpinner = new Spinner(opts);
var gLastUpdated = moment();

/*
 * This function is called every 15 seconds, and refreshes the issues displayed on the page
 */
var refreshAll = function() {
    gSpinner.spin(gSpinTarget);
    if (gData.error) {
        gData = {};
    }
    gData.updated = Date();
    var workOnResponse = function() {
        // This stuff should be done after the ajax response comes back.
        refreshTable();
        gSpinner.stop();
        var now = moment();
        gLastUpdated = now;
        var delay = gRefreshDelay*1000;
        setTimeout(refreshAll, delay);
    };
    $.ajax({
        type: "POST",
        data: JSON.stringify(gData),
        contentType: "application/json",
        url: "./ajax"
    }).done(function(response) {
        gData = JSON.parse(response);
        workOnResponse();
    }).fail(function( jqXHR, textStatus ) {
        gData = {error: "Server error: " + textStatus};
        workOnResponse();
    });
};

/*
 * Takes the new data and replaces the table's content with it
 */
var refreshTable = function() {
    if (gData.error) {
        $('#table-container .row').hide();
        var errorText = '<h1>' + gData.error + '</h1>';
        $('#warning-container').html(errorText);
        $('#warning-container').show();
        return;
    } else {
        $('#warning-container').hide();
        $('#table-container').removeClass('hidden');
        $('#table-container .row').show();
        for (var i in gRows) {
            var rowId = gRows[i];
            var tickets = [];
            // While looping over the issues, keep track of which is the 'worst', severities are
            // based off of bootstrap's built in color-coded classes
            // (danger: red, warning: orange, success: green)
            var worst = 0;
            var worstSeverity = "success";
            var severities = { success: 0, warning: 1, danger: 2, info: 3 };
            for (var j in gData[rowId]) {
                var ticket = gData[rowId][j];
                var state = getState(rowId, ticket);
                tickets.push(buildTicketHTML(state, ticket));
                if (severities[state] > worst) {
                    worstSeverity = state;
                    worst = severities[state];
                }
            }
            $("#" + rowId + " .tickets").html(tickets.join("\n"));
            $("#" + rowId + " .count").removeClass('label-success label-warning label-danger label-info');
            $("#" + rowId + " .count").addClass('label-' + worstSeverity);
            $("#" + rowId + " .count").html(gData[rowId].length);
        }
        var activeTotal = Object.keys(gData.active).length;
        var waitingTotal = Object.keys(gData.waiting).length;
        $("#active.total").html(activeTotal);
        $("#waiting.total").html(waitingTotal);
        $("#total.total").html(activeTotal + waitingTotal);
    }
};

/*
 * Given the ticket data in the form {id: <key>, days: <d>, hours: <h>, minutes: <m>},
 * returns a string of html that will be used to display that in the rows.
 */
var buildTicketHTML = function(state, ticket) {
    var html = '<li><ul class="list-group">';
    if (typeof ticket === 'undefined') {
        html += '<li class="list-group-item list-group-item-success">';
        html += '<h1>No Tickets</h1><br/><br/></li>';
        return html + '</li></ul></li>';
    }
    html += '<li class="list-group-item list-group-item-' + state + '">';
    if(ticket.requestedby && ticket.reviewers.length > 0){
        html += '<span class="pull-left">' + ticket.reviewers.join(',') + '</span> <h4 class="priority glyphicon glyphicon-eye-open info pull-right"></h4>';
    } else {
        html += '<h4 class="pull-right priority ' + getPriorityColor(ticket.priority) + '">' + getPriorityIcon(ticket.priority) + '</h4>';
    }
    var titleParts = ticket.id.split('-');
    var ellipsis = '';
    if(titleParts[0].length > 3) {
        ellipsis = '...';
    }
    var ticketTitle = titleParts[0].substring(0,3) + ellipsis + '-' + titleParts[1];
    html += '<h2>' + ticketTitle + '</h2>';
    if(ticket.requestedby){
        html += '<h4><!-- <span class="glyphicon glyphicon-user"></span> -->From: ' + ticket.requestedby + '</h4>';
    } else {
        html += '<h4><!-- <span class="glyphicon glyphicon-user"></span> -->' + getAssignee(ticket.assignee) + '</h4>';
    }
    html += '<p class="time">';
    if (typeof ticket.total_seconds !== "undefined") {
        if (ticket.total_seconds < 0) {
            html += '<span class="glyphicon glyphicon-exclamation-sign"></span>Missed';
            html += '</p></li></ul></li>';
            return html;
        }
        var days = Math.floor(ticket.total_seconds / 86400);
        var remaining_seconds = ticket.total_seconds - (days * 86400);
        var hours = Math.floor(remaining_seconds / 3600);
        remaining_seconds -= hours * 3600;
        var minutes = Math.floor(remaining_seconds / 60);
        // jic we ever use this again
        remaining_seconds -= minutes * 60;
    } else {
        var days = ticket.days;
        var hours = ticket.hours;
        var minutes = ticket.minutes;
    }
    if (Math.abs(days) > 0) {
        html += days + 'd ';
    }
    html += hours + 'h ' + minutes + 'm</p></li>';
    html += '</li></ul></li>';
    return html;
};


var getPriorityColor = function(priority) {
    switch(priority) {
        case 1 : return "danger";
        case 2 : return "danger";
        case 3 : return "black";
        case 4 : return "black";
        case 5 : return "";
        default : return "info";
    }
};

var getPriorityIcon = function(priority) {
    switch(priority) {
        case 1 : return "P1";
        case 2 : return "P2";
        case 3 : if($('#show-low-priorities').is(':checked') === true){ return "P3" } else { return "&nbsp;";} ;
        case 4 : if($('#show-low-priorities').is(':checked') === true){ return "P4" } else { return "&nbsp;";} ;
        case 5 : if($('#show-low-priorities').is(':checked') === true){ return "P5" } else { return "&nbsp;";} ;
        /*
        case 1 : return "https://jira.mongodb.org/images/icons/priorities/blocker.png";
        case 2 : return "https://jira.mongodb.org/images/icons/priorities/critical.png";
        case 3 : return "https://jira.mongodb.org/images/icons/priorities/major.png";
        case 4 : return "https://jira.mongodb.org/images/icons/priorities/minor.png";
        case 5 : return "https://jira.mongodb.org/images/icons/priorities/trivial.png";
        */
        default : return "&nbsp;";
    }
};

var getAssignee = function(assignee) {
    if(typeof assignee === "undefined" || assignee == '' || assignee == null){
        return "&nbsp;";
    } else {
        if($('#show-assignee').is(':checked') === true) {
            return assignee;
        } else {
            return "&nbsp;";
        }
    }
}
/*
 * Determines the state of a ticket (success, warning, or danger -- from bootstrap),
 * which determines the color of it
 */
var getState = function(rowId, ticket) {
    switch(rowId) {
        case "SLA":
            return getStateSLA(ticket);
        case "FTS":
            return getStateFTS(ticket);
        case "REV":
            return getStateREV(ticket);
        case "UNA":
            return getStateUNA(ticket);
        default:
            return "success";
    }
};

var getStateSLA = function(ticket) {
    if (ticket.total_seconds < 3600) {
        return "danger";
    } else if (ticket.total_seconds < 7200) {
        return "warning";
    } else {
        return "success";
    }
};

var getStateFTS = function(ticket) {
    if (ticket.days === 0 && ticket.hours < 4) {
        return "success";
    } else if (ticket.days === 0 && ticket.hours < 8) {
        return "warning";
    } else {
        return "danger";
    }
};

var getStateREV = function(ticket) {
    if (ticket.hours >= 1 || ticket.days > 0) {
        return "danger";
    } else if (ticket.minutes > 30) {
        return "warning";
    } else {
        return "success";
    }
};

var getStateUNA = function(ticket) {
    return "info";
};

var displayCurrentTime = function() {
    var refresh = 5000;
    var cDate = moment().format("MMM D, HH:mm:ss");
    document.getElementById('currently').innerHTML = cDate;
    var lastUpdated = moment().diff(gLastUpdated);
    document.getElementById('last-updated').innerHTML = moment().diff(gLastUpdated,'seconds');
    if(lastUpdated < gRefreshWarningDelay * 1000){
        $('#updated-container').css('display','none');
    } else {
        $('#updated-container').css('display','block');
    }
    window.setTimeout('displayCurrentTime()', refresh);
};

var drawTimer = function(id, percent, state){
    percent = 100 - percent;
    var html = '<div id="'+ id +'-timer" class="slice sla'+(percent > 50?' gt50':'')+'"><div class="pie sla '+ state +'"></div>'+(percent > 50?'<div class="pie fill sla '+ state +'"></div>':'')+'</div>';
    var deg = 360/100*percent;
    html += '<style>#'+ id +'-timer .pie {-moz-transform: rotate('+deg+'deg); -webkit-transform: rotate('+deg+'deg); -o-transform: rotate('+deg+'deg); transform: rotate('+deg+'deg); border: 1px solid #000;</style>';
    return html;
};

refreshAll();

$(document).ready(function () {
    displayCurrentTime();
});
