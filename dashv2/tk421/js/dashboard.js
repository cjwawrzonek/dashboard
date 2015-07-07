var gRefreshDelay = 15000;
var gRefreshWarningDelay = 30;
var gData = {};
var loaded = false;
var updated = null;
var accessed = null;

var gDataNew = {};

var gRows = ['SLA', 'FTS', 'REV', 'UNA', 'ACTS'];

var hashHandler = function() {
    // alert("hash change");
    var hash = window.location.hash;
    var view = null;
    if (hash == "#Tickets") {
        view = "tickets";
        // alert("View is Tickets");
    } else if (hash == "#Reviews") {
        view = "reviews";
        // alert("View is Reviews");
    } else if (hash == "#Active") {
        view = "active";
    }

    $("div.ticketinfo").each(function(index) {
        var thisOne = $(this);
        var id = $(this).attr('id');
        if (id != "HEAD") {
            if (view == "tickets") {
                if (id != "TICKS") {thisOne.addClass("hidden");}
                else if (id == "TICKS") {thisOne.removeClass("hidden");}
            } else if (view == "reviews") {
                if (id != "REVS") {thisOne.addClass("hidden");}
                else if (id == "REVS") {thisOne.removeClass("hidden");}
            } else if (view == "active") {
                if (id != "ACTIVE") {thisOne.addClass("hidden");}
                else if (id == "ACTIVE") {thisOne.removeClass("hidden");}
            }
        }
    });
}

var workOnResponse = function(str) {
    // This stuff should be done after the ajax response comes back.
    refresh(str);
    $("#" + str + " #ticket-tab tr:odd").addClass("master");
    $("#" + str + " #ticket-tab tr:not(.master)").hide();
    $("#" + str + " #ticket-tab tr:first-child").show();
    $("#" + str + " #ticket-tab tr.master ").click(function(){
        $(this).next("tr").toggle();
        $(this).find(".arrow").toggleClass("up");
    });
};

/*
 * This function is called every 15 seconds, and refreshes the issues displayed on the page
 */
var refreshAll = function() {
    if (gData.error) {
        gData = {};
    }
    if (gDataNew.error) {
        gDataNew = {};
    }
    var date = new Date();
    accessed = date.toISOString();//Date();

    objs = ['SLA', 'FTS', 'UNA', 'REV', 'ACTS'];

    for (var i in objs) {
        var str = objs[i];
        url_str = "./ajax/" + str.toLowerCase();

        $.ajax({
            type: "GET",
            data: JSON.stringify(gDataNew[str]),
            contentType: "application/json",
            url: url_str,
            context: str
        }).done(function(response) {
            gDataNew[this] = JSON.parse(response);
            if (loaded) {
                gDataNew[this].updated = accessed;
            }
            loaded = true;
            workOnResponse(this);
        }).fail(function( jqXHR, textStatus ) {
            gDataNew[this] = {error: "Server error: " + textStatus};
            workOnResponse(this);
        }); 
    }
    var delay = gRefreshDelay*1000;
    setTimeout(refreshAll, delay);
};

var refresh = function(str) {
    if (gDataNew[str].error) {
        $('#table-container .row').hide();
        var errorText = '<h1>' + gDataNew[str].error + '</h1>';
        $('#warning-container').html(errorText);
        $('#warning-container').show();
        return;
    } else {
        var rows = [];

        var worst = 0;
        var worstSeverity = "success";
        var severities = { success: 0, warning: 1, danger: 2, info: 3 };

        for (var j in gDataNew[str][str]) {
            var ticket = gDataNew[str][str][j];
            var state = getState(str, ticket);
            if (str != "REV") {
                rows.push(buildRowHTML(state, ticket));
            } else {
                rows.push(buildReviewHTML(state, ticket));
            }

            if (severities[state] > worst) {
                worstSeverity = state;
                worst = severities[state];
            }
        }
        $("#" + str + " .trows").html(rows.join("\n"));
        $("#" + str + " .count").removeClass('label-success label-warning label-danger label-info');
        $("#" + str + " .count").addClass('label-' + worstSeverity);
        $("#" + str + " .count").html(gDataNew[str][str].length);
    }
};

var buildRowHTML = function(state, ticket) {
    var missed = false;
    if (typeof ticket.total_seconds !== "undefined") {
        if (ticket.total_seconds < 0) {
            missed = true;
        } else {
            var days = Math.floor(ticket.total_seconds / 86400);
            var remaining_seconds = ticket.total_seconds - (days * 86400);
            var hours = Math.floor(remaining_seconds / 3600);
            remaining_seconds -= hours * 3600;
            var minutes = Math.floor(remaining_seconds / 60);
            // jic we ever use this again
            remaining_seconds -= minutes * 60;
        }
    } else {
        var days = ticket.days;
        var hours = ticket.hours;
        var minutes = ticket.minutes;
    }
    if (state == "success") {
        var html = '<tr class="trow master noselection " style="background-color: #D0D0D0;" data-toggle="collapse" \
            data-target="demo1">\n<td colspan="2"><a class="key" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2"';
    } else if (state == "warning") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(28, 80%, 70%);" \
            data-toggle="collapse" data-target="demo1">\n<td colspan="2"><a class="key" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2"';
    } else if (state == "danger") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(0, 100%, 76%);" \
            data-toggle="collapse" data-target="demo1">\n<td colspan="2"><a class="key" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2"';
    } else {
        var html = '<tr class="trow master noselection " style="background-color: #D0D0D0;" data-toggle="collapse" data-target="demo1">\n<td colspan="2"><a class="key" \
            href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2" class="clickable"';
    }
    if (missed) {
        html += 'class="label-danger">\nMissed';
    } else {
        html += '>\n';
        if (Math.abs(days) > 0) {
            html += days + 'd ';
        }
        html = html + hours + 'h ' + minutes + 'm';
    }
    html = html + '</td>\n<td colspan="1">' + ticket.priority;
    html = html + '</td>\n<td colspan="2">' + getAssignee(ticket.assignee) + '</td>';
    html += '<td colspan="5" style="width:40%;overflow:hidden;">\n';
    html += ticket.desc;
    html += '</td></tr>\
        <tr><td colspan="3"><div class="collapse in" id="demo1"><button type="button" class="btn my-btn">Ping Team</button></div></td>\
        </td><td colspan="3"><div class="collapse in" id="demo1"><button type="button" class="btn my-btn">Claim Ticket</button></div></td>\
        <td colspan="6"><div class="collapse in" id="demo1">\
        <form action="demo_form.asp">Dev Comment: <input type="text" name="fname"><input type="submit" value="Submit"></form></div></td></tr>';
    return html;
    // }
}

var buildReviewHTML = function(state, ticket) {
    var days = ticket.days;
    var hours = ticket.hours;
    var minutes = ticket.minutes;

    if (state == "success") {
        // var html = '<tr class="trow master " style="background-color: hsl(96, 45%, 64%);" data-toggle="collapse" data-target="demo1">\n<td>' + ticket.id + '</td>\n<td';
        var html = '<tr class="trow master noselection " style="background-color: #D0D0D0;" data-toggle="collapse" \
            data-target="demo1">\n<td><a class="key " href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
    } else if (state == "warning") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(28, 80%, 70%);" \
            data-toggle="collapse" data-target="demo1">\n<td><a class="key " href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
    } else if (state == "danger") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(0, 100%, 76%);" \
            data-toggle="collapse" data-target="demo1">\n<td><a class="key " href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
    } else {
        var html = '<tr class="trow master noselection " style="background-color: #D0D0D0;" data-toggle="collapse" \
            data-target="demo1">\n<td><a class="key " href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
    }
    html += '>\n';
    if (Math.abs(days) > 0) {
        html += days + 'd ';
    }
    html = html + hours + 'h ' + minutes + 'm';

    html = html + '</td>\n<td>' + ticket.requestedby;
    html += '</td>\n<td>';
    for (var i in ticket.reviewers) {
        html = html + ticket.reviewers[i] + ", ";
    }
    html += '</td>';
    html += '<td style="width:40%;overflow:hidden;">\n';
    for (var i in ticket.lgtms) {
        html = html + ticket.lgtms[i] + ", ";
    }
    html += '</td></tr>\
    <tr><td><div class="collapse in" id="demo1">\
        <button type="button" class="btn my-btn">\
        Ping Team\
        </button></div></td>\
    <td><div class="collapse in" id="demo1">\
        <button type="button" class="btn my-btn">\
        Needs Work\
        </button></div></td>\
    <td><div class="collapse in" id="demo1">\
        <button type="button" class="btn my-btn">\
        Looking\
        </button></div></td>\
    <td><div class="collapse in" id="demo1">\
        <button type="button" class="btn my-btn">\
        LGTM\
        </button></div></td>\
    <td><div class="collapse in" id="demo1">\
        <button type="button" class="btn my-btn">\
        Close\
        </button></div></td></tr>';
    return html;
    // }
}

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
        // if($('#show-assignee').is(':checked') === true) {
        //     return assignee;
        // } else {
        //     return "&nbsp;";
        // }
        return assignee;
    }
}
/*
 * Determines the state of a ticket (success, warning, or danger -- from bootstrap),
 * which determines the color of it
 */
var getState = function(str, ticket) {
    str = str.toString();
    switch(str) {
        case "SLA":
            return getStateSLA(ticket);
        case "FTS":
            return getStateFTS(ticket);
        case "REV":
            return getStateREV(ticket);
        case "UNA":
            return getStateUNA(ticket);
        default:
            return "default";
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

refreshAll();

$( document ).ready(function() {
    hashHandler();
});