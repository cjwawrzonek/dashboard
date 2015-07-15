function setDecision(type, text, next){
    $('#decisionType').removeClass('alert-success alert-danger alert-warning');
    if(type == 'no') {
        $('#decisionType').addClass('alert-danger');
    } else if(type == 'maybe') {
        $('#decisionType').addClass('alert-warning');
    } else {
        $('#decisionType').addClass('alert-success');
    }
    $('#decision').html(text);
    $('#decisionType').show();
    if(next !== undefined && next !== null) {
        return next();
    }
}

var hideDay = function() {
    $('#selDay').val('');
    $('#divDay').hide();
};

var showDay = function() {
    $('#selDay').val('');
    $('#divDay').show();
};

var hideLocation = function() {
    $('#selLocation').val('');
    $('#divLocation').hide();
};

var showLocation = function() {
    $('#selLocation').val('');
    $('#divLocation').show();
};

var hideWR = function(){
    $('#selWR').val('');
    $('#divWR').hide();
};

var showWR = function(){
    $('#selWR').val('');
    $('#divWR').show();
};

var hidePriority = function(){
    $('#selPriotiy').val('');
    $('#divPriority').hide();
};

var showPriority = function(){
    $('#selPriotiy').val('');
    $('#divPriority').show();
};

var processLocation = function() {
    hideDay();
    hideWR();
    hidePriority();
    var location = $(this).val();
    setDecision("maybe","Need more information...", showDay);
};

var processDay = function() {
    hideWR();
    hidePriority();
    var day = $(this).val();
    var location = $('#selLocation').val();
    if(location == "Tel Aviv"){
        if(day == "Friday") {
            setDecision("no", "No.");
        } else if(day == "Sunday") {
            setDecision("yes","Yes! It is a workday. But remember you should only be responding to customers whose work week includes Sunday.");
        } else {
            setDecision("maybe","Not sure yet...", showWR);
        }
    } else if(day == "Saturday" || day == "Sunday") {
        setDecision("maybe","Not sure yet...", showWR);
    } else {
        setDecision("yes","Yes!");
    }
};

var processWR = function() {
    hidePriority();
    var wr = $(this).val();
    if(wr == "yes") {
        setDecision("maybe","One more question...", showPriority);
    } else {
        setDecision("no","No.");
    }
};

var processPriority = function() {
    var priority = $(this).val();
    if(priority == "P1" || priority == "P2") {
        setDecision("yes","Yes! If you are weekend responder, please respond to customer.");
    } else if(priority == "P3") {
        setDecision("no","No. Unless this is an issue that would soon become a P1/P2, do not respond.");
    } else {
        setDecision("no","No. This can wait until a weekday.");
    }
};

$(document).ready(function() {
    $('#selDay').change(processDay);
    $('#selLocation').change(processLocation);
    $('#selWR').change(processWR);
    $('#selPriority').change(processPriority);
});
