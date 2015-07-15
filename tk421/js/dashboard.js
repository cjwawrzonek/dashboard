var pollDelay = 15;
var gRefreshWarningDelay = 30;
var gData = {};
var loaded = false;
var updated = null;
var accessed = null;
var user = {};

var allData = {};

// ############################################################################
/* Structure */

/* These are the main views (tabs on the left). There's one AJAX call for each 
of them. Each view has a set of data wells that it displays, which are 
returned as dictionaries within each view.
TC = Traffic Cop
REVS = Reviews
ACTS = All Active Tickets
WAITS = Tickets Waiting for Customer
USER = All Tickets Related to the user*/
var dataViews = ['TC', 'REVS', 'ACTS', 'WAITS', 'USER', 'UNAS'];
// ############################################################################

// Pretty straightforward. On hash change, call hashHandler() to switch views
var hashHandler = function() {
    var hash = window.location.hash;
    var view = null;
    $('.view').css('background-color', 'transparent');
    if (hash == "#Tcop") {
        view = "tcop";
    } else if (hash == "#Reviews") {
        view = "revs";
    } else if (hash == "#Una") {
        view = "unas";
    } else if (hash == "#Active") {
        view = "acts";
    } else if (hash == "#Waiting") {
        view = "waits";
    } else if (hash == "#User") {
        view = "user";
    }
    $('.' + view).css('background-color', 'black');

    $("div.ticketinfo").each(function(index) {
        var thisOne = $(this);
        var id = $(this).attr('id');
        if (view == "tcop") {
            if (id != "TCOP" && id != "NOUSER") {thisOne.addClass("hidden");}
            else if (id == "TCOP") {thisOne.removeClass("hidden");}
        } else if (view == "revs") {
            if (id != "REVS" && id != "NOUSER") {thisOne.addClass("hidden");}
            else if (id == "REVS") {thisOne.removeClass("hidden");}
        } else if (view == "acts") {
            if (id != "ACTIVE" && id != "NOUSER") {thisOne.addClass("hidden");}
            else if (id == "ACTIVE") {thisOne.removeClass("hidden");}
        } else if (view == "unas") {
            if (id != "UNAS" && id != "NOUSER") {thisOne.addClass("hidden");}
            else if (id == "UNAS") {thisOne.removeClass("hidden");}
        } else if (view == "waits") {
            if (id != "WAITING" && id != "NOUSER") {thisOne.addClass("hidden");}
            else if (id == "WAITING") {thisOne.removeClass("hidden");}
        } else if (view == "user") {
            if (id != "USER" && id != "NOUSER") {thisOne.addClass("hidden");}
            else if (id == "USER") {thisOne.removeClass("hidden");}
        }
    });
};

var repeatRefresh = function() {
    console.log("starting repeatRefresh");
    refreshData(dataViews);
    var delay = pollDelay*1000;
    setTimeout(repeatRefresh, delay);
}

/* This function is called every 'pollDelay' seconds, and refreshes the 
data for each view passed in 'views' */
var refreshData = function(views) {
    if (allData.error) {
        allData = {};
    }
    var date = new Date();
    accessed = date.toISOString();//Date();

    for (var i in views) {
        var view = views[i];
        url_str = "./ajax/" + view.toLowerCase();

        $.ajax({
            type: "GET",
            // data: JSON.stringify(allData[view]),
            // contentType: "application/json",
            url: url_str,
            context: view
        }).done(function(response) {
            allData[this] = JSON.parse(response);
            if (loaded) {
                allData[this].updated = accessed;
            }
            loaded = true;
            onResponse(this);
        }).fail(function( jqXHR, textStatus ) {
            allData[this] = {error: "Server error: " + textStatus};
            onResponse(this);
        }); 
    }
};

// This stuff should be done after the ajax response comes back
var onResponse = function(view) {
    refresh(view);
    if (view != "TC" && view != "USER") {
        // tag = "." + view.toLowerCase(); + "-count";
        if (view == "REVS") {
            $(".revs-count").html(allData.REVS.REV.length);
        } else if (view == "UNAS") {
            $(".unas-count").html(allData.UNAS.UNAS.length);
        } else if (view == "WAITS") {
            $(".waits-count").html(allData.WAITS.WAIT.length);
        } else if (view == "ACTS") {
            $(".acts-count").html(allData.ACTS.ACTS.length);
        }
    }
    // This is for the expanding row functionality. Don't worry about it
    // too much. I'm switching to bootstrap's accordion library soon
    for (var dataName in allData[view]) {
        $("#" + dataName + " #ticket-tab tr:odd").addClass("master");
        $("#" + dataName + " #ticket-tab tr:not(.master)").hide();
        $("#" + dataName + " #ticket-tab tr:first-child").show();
        $("#" + dataName + " #ticket-tab tr.master ").click(function(){
            $(this).next("tr").toggle();
            $(this).find(".arrow").toggleClass("up");
        });
    }
};

// This refreshes the html for a single view (tab) give the data for that view
var refresh = function(view) {
    if (allData[view].status == 'error') {
        $('.table-container').hide();
        var errorText = '<h1>Error: ' + allData[view]['message'] + '</h1>';
        $('.warning-container').html(errorText);
        $('.warning-container').removeClass("hidden");
        return "error";
    } else {
        for (var dataWell in allData[view]) {
            var rows = [];

            var worst = 0;
            var worstSeverity = "success";
            var severities = { success: 0, warning: 1, danger: 2, info: 3 };

            for (var t in allData[view][dataWell]) {
                var ticket = allData[view][dataWell][t];
                var state = getState(dataWell, ticket);
                // Reviews are built differently than issues. I might combine
                // these calls later
                if (dataWell != "REV") {
                    rows.push(buildRowHTML(state, ticket));
                } else {
                    rows.push(buildReviewHTML(state, ticket));
                }
                if (severities[state] > worst) {
                    worstSeverity = state;
                    worst = severities[state];
                }
            }
            $("#" + dataWell + " .trows").html(rows.join("\n"));
            $("#" + dataWell + " .count").addClass('label-' + worstSeverity);
            $("#" + dataWell + " .count").html(allData[view][dataWell].length);
        }
    }
};

// Yes I know these are a mess...
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
            data-target="demo1">\n<td colspan="2"><a class="key" target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2"';
    } else if (state == "warning") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(28, 80%, 70%);" \
            data-toggle="collapse" data-target="demo1">\n<td colspan="2"><a class="key" target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2"';
    } else if (state == "danger") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(0, 100%, 76%);" \
            data-toggle="collapse" data-target="demo1">\n<td colspan="2"><a class="key" target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2"';
    } else {
        var html = '<tr class="trow master noselection " style="background-color: #D0D0D0;" data-toggle="collapse" data-target="demo1">\n<td colspan="2"><a class="key" \
            target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td colspan="2" class="clickable"';
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
    html += '</td></tr><tr><td></td></tr>';
        // <tr><td colspan="3"><div class="collapse in" id="demo1"><button type="button" class="btn my-btn">Ping Team</button></div></td>\
        // </td><td colspan="3"><div class="collapse in" id="demo1"><button type="button" class="btn my-btn">Claim Ticket</button></div></td>\
        // <td colspan="6"><div class="collapse in" id="demo1">\
        // <form action="demo_form.asp">Dev Comment: <input type="text" name="fname"><input type="submit" value="Submit"></form></div></td></tr>';
    return html;
}

// This variable is a quick hack. This NEEDS to change. -------------
var added = false;
// ------------------------------------------------------------------

// And this one is a mess as well.
var buildReviewHTML = function(state, ticket) {
    var days = ticket.days;
    var hours = ticket.hours;
    var minutes = ticket.minutes;

    if (state == "success") {
        // var html = '<tr class="trow master " style="background-color: hsl(96, 45%, 64%);" data-toggle="collapse" data-target="demo1">\n<td>' + ticket.id + '</td>\n<td';
        var html = '<tr class="trow master noselection " style="background-color: hsl(96, 45%, 64%);" data-toggle="collapse" \
            data-target="demo1">\n<td><a class="key " target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
    } else if (state == "warning") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(28, 80%, 70%);" \
            data-toggle="collapse" data-target="demo1">\n<td><a class="key " target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
    } else if (state == "danger") {
        var html = '<tr class="trow master noselection " style="background-color: hsl(0, 100%, 76%);" \
            data-toggle="collapse" data-target="demo1">\n<td><a class="key " target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
    } else {
        var html = '<tr class="trow master noselection " style="background-color: #D0D0D0;" data-toggle="collapse" \
            data-target="demo1">\n<td><a class="key " target="_blank" href="' + 'https://jira.mongodb.org/browse/' + ticket.id + '">' + ticket.id + '</td>\n<td';
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
    if (ticket.reviewers.length > 0) {html = html.substring(0, html.length - 2);}
    html += '</td>';
    html += '<td style="width:40%;overflow:hidden;">\n';
    for (var i in ticket.lgtms) {
        html = html + ticket.lgtms[i] + ", ";
    }

    if (!added) {var text = "Review";} 
    else {var text = "Un-Review";}

    if (ticket.lgtms.length > 0) {html = html.substring(0, html.length - 2);}
    html = html + '</td></tr>\
    <tr><td><div class="collapse in" id="demo1">\
        <button type="button" onclick="reviewerClick(this.value)"\
        value="' + ticket.id + '" \
        class="btn my-btn">' + text + '\
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
        </button></div></td>\
    <td><div class="collapse in" id="demo1">\
        </div></td></tr>';
    return html;
        // <td><div class="collapse in" id="demo1">\
        // <button type="button" onclick="removeReviewer(this.value)"\
        // value="' + ticket.id + '" \
        // class="btn my-btn">\
        // Un-Review\
        // </button></div></td>\
}

var reviewerClick = function(key) {
    if (!added) {
        addReviewer(key);
        added = true;
    } else {
        removeReviewer(key);
        added = false;
    }

}

var addReviewer = function(key) {
    url_str = "./reviews/" + key + "/reviewer/self";
    console.log(url_str);
    $.ajax({
        type: "PUT",
        // data: JSON.stringify(allData[view]),
        contentType: "application/json",
        url: url_str,
        context: key
    }).done(function(response) {
        // var change = JSON.parse(response);
        console.log(response);
    }).fail(function( jqXHR, textStatus ) {
        alert('failure in addReviewer');
    });
    console.log(key);
    refreshData(['REVS']);
}

var removeReviewer = function(key) {
    url_str = "./reviews/" + key + "/unreview/self";
    console.log(url_str);
    $.ajax({
        type: "PUT",
        // data: JSON.stringify(allData[view]),
        contentType: "application/json",
        url: url_str,
        context: key
    }).done(function(response) {
        // var change = JSON.parse(response);
        console.log(response);
    }).fail(function( jqXHR, textStatus ) {
        alert('failure in removeReviewer');
    }); 
    console.log(key);
    refreshData(['REVS']);
}

var addLooking = function(key) {
    url_str = "./reviews/" + key + "/looking/self";
    console.log(url_str);
    $.ajax({
        type: "PUT",
        // data: JSON.stringify(allData[view]),
        contentType: "application/json",
        url: url_str,
        context: key
    }).done(function(response) {
        // var change = JSON.parse(response);
        console.log(response);
    }).fail(function( jqXHR, textStatus ) {
        alert('failure in addLooking');
    });
    console.log(key);
    refreshData(['REVS'])
}

var removeLooking = function(key) {
    url_str = "./reviews/" + key + "/unlooking/self";
    console.log(url_str);
    $.ajax({
        type: "PUT",
        // data: JSON.stringify(allData[view]),
        contentType: "application/json",
        url: url_str,
        context: key
    }).done(function(response) {
        // var change = JSON.parse(response);
        console.log(response);
    }).fail(function( jqXHR, textStatus ) {
        alert('failure in removeLooking');
    });
    console.log(key);
    refreshData(['REVS'])
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
        default : return "&nbsp;";
    }
};

var getAssignee = function(assignee) {
    if(typeof assignee === "undefined" || assignee == '' || assignee == null){
        return "&nbsp;";
    } else {
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

var logIn = function() {
    // this indicates that we've loaded the user
    var usr_name = $.cookie('dash_usr_name');
    if ((! usr_name) || (usr_name == "null")) {
        userInit();
    } else {
        $("#usr_name_space").text(usr_name);
        $(".dash-user-name").text(usr_name);
    }
    $(".log-link").text("Log Out");
    $(".usr-alerts").html(alert_str);
    $("div #USER").show();
    $("div #TCOP").show();
    $("div #REVS").show();
    $("div #UNAS").show();
    $("div #ACTIVE").show();
    $("div #WAITING").show();
    $("div #NOUSER").hide();
    $("div #NOUSER").addClass('hidden');
};

var toggleLog = function() {
    name = $.cookie('dash_usr_name');
    if (!name || name == "null") {logIn();}
    else {logOut();}
}

var userInit = function() {
    var urlString = "/login";
    $.get(urlString).done(function(res) {
        // TODO if successful, set usr_token and reload
        user = JSON.parse(res);
        $.cookie('dash_usr_name', user['name']);
        $("#usr_name_space").text(user['name']);
        $(".dash-user-name").text(user['name']);
        // window.location.reload();
    });
};

var logOut = function() {
    $.cookie('dash_usr_name', null, {path: '/'});
    $("#usr_name_space").text("No Login");
    $(".dash-user-name").text("No Login");
    $(".log-link").text("Log In");
    $(".usr-alerts").html("<h4>Log in Please</h4>");
    $("div #USER").hide();
    $("div #TCOP").hide();
    $("div #REVS").hide();
    $("div #UNAS").hide();
    $("div #ACTIVE").hide();
    $("div #WAITING").hide();
    $("div #NOUSER").show();
    $("div #NOUSER").removeClass('hidden');
};

/* These are the first views to be loaded as they are the most critical
to the viewer. */
var firstViews = ['TC', 'REVS', 'USER'];
refreshData(firstViews);

// This is just a little HTML for demo purposes. This will be replaced with 
// actual functionality later...
var alert_str = '<li class="message-footer">Not Implemented\
    <a href="#">Read All New Messages</a></li>';

$( document ).ready(function() {
    hashHandler();
    logIn();
    refreshData(['ACTS', 'UNAS', 'WAITS'])
    // Now, all data has been manually loaded, so 
    // set a timeout and then call the polling refreshser
    setTimeout(repeatRefresh, 15000);
});
