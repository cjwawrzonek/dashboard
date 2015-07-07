$(document).ready(function() {
    $(document).bind('keydown', '/', function () {
        if ($("input,textarea").is(":focus")) {
            return true;
        } else {
            $('#groupSearch').focus();
            return false;
        }
    });
    $('.failedtests').popover();
    $('.tooltip').tooltip();
    $('.metadata').tooltip();
    userInit();
});

var deleteCookies = function() {
    var cookies = document.cookie.split(";");
    for (var i = 0; i < cookies.length; i++) {
        name = cookies[i].split('=')[0]
        $.removeCookie(name);
    }
}

/*
var groups = new Bloodhound({
  datumTokenizer: Bloodhound.tokenizers.obj.whitespace('GroupName'),
  queryTokenizer: Bloodhound.tokenizers.whitespace,
  remote: '/groups/1/%QUERY'
});

groups.initialize();

var suggestionTemplate = Handlebars.compile('<p><a href="/group/{{GroupId}}"><strong>{{GroupName}}</strong></a></p>');

$('#search2').typeahead(
    {
        hint: true,
        highlight: true,
        minLength: 3
    },
    {
        name: 'autocomplete',
        source: groups.ttAdapter(),
        displayKey: 'GroupName',
        templates: {
            empty: '<div>No matches found...</div>',
            suggestion: suggestionTemplate
        }
    }
).bind("typeahead:selected", function (obj,datum){
	window.location = "/group/" + datum.GroupId;
}).keypress(function (e) {
  if (e.which == 13) {
    return false;
  }
});
*/

var userInit = function() {
    // this indicates that we've loaded the user
    var kk_token = $.cookie('kk_token');
    if (! kk_token) {
        var urlString = "/login";
        $.post(urlString).done(function(res) {
            // TODO if successful, set kk_token and reload
            $.cookie('kk_token', 1);
            window.location.reload();
        });
        return null;
    }

    var user = $.cookie('user');
    if (user) {
        $("#nav_span_user").text("whoami: "+user);
    }
};
