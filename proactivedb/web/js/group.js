$('#myTab a').click(function (e) {
      e.preventDefault()
      $(this).tab('show')
})

addNoteToGroup = function() {
    // create new edit field and maybe submit it
    // only one note at a time folks
    $("#a_addNoteToGroup").css("visibility", "hidden");
    var containerDiv = document.createElement("div");
    var textInput = $('<textarea class="form-control"/>');
    $(textInput).attr("id", "textInput_newNoteText");
    okButton = document.createElement("button");
    $(okButton).text("ok").addClass("btn btn-primary");
    $(okButton).click(function() {
        console.log("submitting note!");
        gid = $("#gid").val()
        data = {'gid': gid, 'text': $(textInput).val()}
        $.ajax({
            type: "POST",
            url: "/addnote",
            data: JSON.stringify(data),
            dataType: "json"
        }).success(function(res) {
            console.log("success!");
            note = res['data'];
            $(containerDiv).remove();
            newNoteDiv = document.createElement("div");
            $(newNoteDiv).addClass('div_note');
            $(newNoteDiv).attr('id', note['sfid']);
            textSpan = document.createElement("span");
            textSpan.innerHTML = note['text']+' ';
            $(textSpan).addClass("editable");
            textSpan.addEventListener("click", editableClickFunction);
            dt = new Date(parseInt(note['createdDateTS'])*1000)
            dtstring = dt.toISOString().slice(0, -5)
            $(newNoteDiv).text(''+note['author']+'@'+dtstring+': ');
            $(newNoteDiv).append(textSpan);
            deleteAnchor = document.createElement("a");
            deleteAnchor.href = "javascript:deleteNote('"+note['sfid']+"')";
            deleteAnchor.innerHTML = "X";
            $(newNoteDiv).append(deleteAnchor);
            $("#div_notes").prepend(newNoteDiv);
            $("#a_addNoteToGroup").css("visibility", "visible");
        }).error(function(res) {
            console.log("error saving note");
            console.log(res);
        });
    });
    cancelButton = document.createElement("button");
    $(cancelButton).text("cancel").addClass("btn btn-default");
    $(cancelButton).click(function() {
        console.log("cancelling...");
        $(containerDiv).remove()
        $("#a_addNoteToGroup").css("visibility", "visible");
    });
    var buttonDiv = $('<div class="pull-right"></div>');
    $(containerDiv).append(textInput);
    $(buttonDiv).append(okButton);
    $(buttonDiv).append(cancelButton);
    $(containerDiv).append(buttonDiv);
    $("#div_notes").prepend(containerDiv);
}

addToTicket = function(button, testId) {
    console.log("addToTicket");
    header = $("#div_failedtests_"+testId+" div.header").text();
    comment = $("#div_failedtests_"+testId+" div.comment").text();
    // new div
    ticketBody = document.getElementById("div_ticketDescription_mainBody");
    div = document.createElement("div");
    $(div).attr('data-testid',testId);
    $(div).attr('id',"div_ticketDescription_"+testId);
    $(div).addClass("testComment");
    headerDiv = document.createElement("div");
    $(headerDiv).addClass("header");
    $(headerDiv).addClass("editable");
    $(headerDiv).text("h5. "+header);
    headerDiv.addEventListener("click", editableClickFunction);
    commentDiv = document.createElement("div");
    $(commentDiv).addClass("comment");
    $(commentDiv).addClass("editable");
    $(commentDiv).text(comment);
    commentDiv.addEventListener("click", editableClickFunction);
    div.appendChild(headerDiv);
    div.appendChild(commentDiv);
    ticketBody.appendChild(div);
    ticketBody.appendChild(document.createElement("br"));
    ftdiv = $("#div_failedtests_"+testId);
    ftdiv.addClass("alert-info");

    // change button
    $(button).text("Remove from ticket");
    button.onclick = function() {removeFromTicket(button, testId)};
};

deleteNote = function(sfid) { 
    $.ajax({
        type: "POST",
        url: "/deletenote",
        data: JSON.stringify({'sfid': sfid}),
        dataType: "json"
    }).success(function(res) {
        console.log(res);
        $("#"+sfid).remove()
    });
};

removeFromTicket = function(button, testId) {
    console.log("removeFromTicket");
    console.log(testId);
    div = document.getElementById("div_ticketDescription_"+testId);
    if (div) {
        div.parentNode.removeChild(div);
        $(button).text("Add to ticket");
        button.onclick = function() {addToTicket(button, testId)};

        ftdiv = $("#div_failedtests_"+testId);
        ftdiv.removeClass("alert-info");
    } else {
        console.log("div_ticketDescription_"+testId+" dne!");
    }
};

saveStateAndSetToEditable = function(cb) {
    console.log("beingedited -> editable");
    content = $("#beingedited textarea").val();

    el = $("#beingedited")
    el.html(content)

    // is this a change we have to persist to the backend?
    if (el.parent().hasClass("div_note")) {
        //TODO did anything actually change? if not, there's nothing to persist
        console.log("Persisting change to salesforce");
        datum = {'sfid': el.parent().attr('id'), 'text': content}

        $.ajax({
            type: "POST",
            url: "/editnote",
            data: JSON.stringify(datum),
            dataType: "json"
        }).done(function(res) {
            console.log(res);
        });
    };

    el.attr('id', '');
    if (typeof cb !== "undefined") {
        cb();
    }
};

editableClickFunction = function(e) {
    // User wants to edit the content in this div
    // Get div content and replace it with a textarea of the same content
    div = e.target;

    div.id = "beingedited";
    content = $(div).text();
    height = $(div).height();
    ta = document.createElement("textarea");
    ta.value = content;
    $(ta).css('height', height*1.1);
    div.innerHTML = null;
    div.appendChild(ta);
};

/*
$('div.editable').click(function(e) {
    return editableClickFunction(e);
});
*/

document.addEventListener("click", function(e) {
    // If the user clicks on an editable element not being edited, save the
    // state and move it back to editable
    if (e.target.parentNode.id !== "beingedited" && document.getElementById("beingedited")) {
        saveStateAndSetToEditable();
    }
    if (($(e.target).hasClass("editable"))) {
        editableClickFunction(e);
    }
});

$("#a_createTicket").click(function(e) {
    // make sure they are really really really sure
    var answer = window.prompt("Are you sure you want to do this? If you type 'YES' a ticket WILL be created!");
    if (answer !== "YES") {
        return;
    }

    // freeze in progress changse
    createTicket = function() {
        var group = $("#jira_group").val();
        var gid = $("#gid").val();
        var summary = $("#div_ticketSummary").text().trim();
        var project = "CS";

        var intro = "";
        $($('#div_ticketDescription_mainBody').prevAll().get().reverse()).each(function(){
            intro += $(this).text().trim() + '\n'
        });

        var tests = [];
        $('#div_ticketDescription_mainBody .testComment').each(function() {
            var testId = $(this).attr('data-testid');
            var testContent = "";
            $(this).find('.editable').each(function() {
                testContent = testContent + $(this).text().trim() + '\n';
            });
            var test = {};
            test[testId] = testContent + '\n';
            tests.push(test);
        });

        var outro = "";
        $('#div_ticketDescription_mainBody').nextAll().each(function(){
            outro += $(this).text().trim() + '\n';
        });

        var data = {'group': group,'project': project, 'gid': gid, 'summary': summary, 'intro': intro, 'outro': outro, 'tests':tests};

        $.ajax({
            type: "POST",
            url: "/issue",
            data: JSON.stringify(data),
            dataType: "json"
        }).done(function(res) {
            console.log(res);
            alert("Ticket created: " + res['data']['issue']);
        });
    };
    saveStateAndSetToEditable(createTicket);
});

$("#a_previewTicket").click(function(e) {
    var group = $("#jira_group").val();
    $("#active_jira_group").text('('+group+')');
    var gid = $("#gid").val();
    var summary = $("#div_ticketSummary").text().trim();
    var project = "CS";

    var intro = "";
    $($('#div_ticketDescription_mainBody').prevAll().get().reverse()).each(function(){
        intro += $(this).text().trim() + '\n';
    });

    var tests = [];
    $('#div_ticketDescription_mainBody .testComment').each(function() {
        var testId = $(this).attr('data-testid');
        var testContent = "";
        $(this).find('.editable').each(function() {
            testContent = testContent + $(this).text().trim() + '\n';
        });
        var test = {};
        test[testId] = testContent + '\n';
        tests.push(test);
    });

    var outro = "";
    $('#div_ticketDescription_mainBody').nextAll().each(function(){
        outro += $(this).text().trim() + '\n';
    });

    var data = {'group': group,'project': project, 'gid': gid, 'summary': summary, 'intro': intro, 'outro': outro, 'tests':tests};

    $.ajax({
        type: "POST",
        url: "/previewissue",
        data: JSON.stringify(data),
        dataType: "json"
    }).done(function(res) {
        var ticketContent = res['data'].trim();
        $('#ticketPreview').html(jQuery.parseHTML(ticketContent));
        $('#previewModal').modal();
    });
});
