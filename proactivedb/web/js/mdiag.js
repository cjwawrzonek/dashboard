var dropzone = new Dropzone('#dropzone', {
    parallelUploads: 100,
    maxFilesize: 30,
    filesizeBase: 1000,
    url: "/mdiag/upload",
    acceptedFiles: ".json",
    autoProcessQueue: false,
    maxFiles: 1,

    init: function () {
        var myDropzone = this;
        $('#test-mdiag-btn').click(function (e) {
            e.preventDefault();
            e.stopPropagation();
            myDropzone.processQueue();
        });

        myDropzone.on("sending", function(file, xhr, formData) {
            formData.append("jiraid",$('input[id="jira"]').val());
        });

        myDropzone.on("success", function(file,response) {
            var results = JSON.parse(response);
            processResults(results.payload);
        });
    }
});

var processResults = function(results) {
    for(var r in results){
        var result = results[r];
        var row = $('<tr><td>' + result.header + '</td><td>' + result.comment + '</td><td>' + processStatus(result.pass) + '</td></tr>');
        $('#resultsTableBody').append(row);
    }
    $('#resultsPanel').show()
};

var processStatus = function(status) {
    if(status === true){
        return '<i class="btn btn-success glyphicon glyphicon-ok"></i>'
    } else {
        return '<i class="btn btn-danger glyphicon glyphicon-remove"></i>'
    }
};

var findJiraTicketCustomer = function(jira_key,location) {
    if(jira_key != "") {
        $.ajax({
            type: "GET",
            url: "/mdiag/ticketinfo/" + jira_key,
            datatype: "json"
        }).success(function (response) {
            var json = JSON.parse(response);
            return location.val(json.company);
        });
    }
};

$(document).ready(function() {
    $('input[id="jira"]').on('blur',function(){
        findJiraTicketCustomer($(this).val(),$('input[id="customer"]'));
        if($(this).val() != '') {
            $('#uploadPanel').show();
            $('#submitPanel').show();
        } else {
            $('#uploadPanel').hide();
            $('#submitPanel').hide();
        }
    });
});