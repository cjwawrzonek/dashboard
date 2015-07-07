// Get the template HTML and remove it from the doumenthe template HTML and remove it from the doument
/*
var previewNode = document.querySelector("#template");
previewNode.id = "";
var previewTemplate = previewNode.parentNode.innerHTML;
previewNode.parentNode.removeChild(previewNode);
 
var myDropzone = new Dropzone(document.body, { // Make the whole body a dropzone
  url: "/upload", // Set the url
  thumbnailWidth: 80,
  thumbnailHeight: 80,
  parallelUploads: 20,
  previewTemplate: previewTemplate,
  autoQueue: false, // Make sure the files aren't queued until manually added
  previewsContainer: "#previews", // Define the container to display the previews
  clickable: ".fileinput-button", // Define the element that should be used as click trigger to select files.
  maxFiles: 1,
  accept: function(file, done) {
    console.log("uploaded");
    done();
  },
  init: function() {
    this.on("maxfilesexceeded", function(file){
        alert("No more files please!");
    });
  }
});

myDropzone.on("addedfile", function(file) {
  // Hookup the start button
  file.previewElement.querySelector(".start").onclick = function() { myDropzone.enqueueFile(file); };
});
 
// Update the total progress bar
myDropzone.on("totaluploadprogress", function(progress) {
  document.querySelector("#total-progress .progress-bar").style.width = progress + "%";
});
 
myDropzone.on("sending", function(file, xhr, formData) {
  formData.append("category", "group_report");
  // Show the total progress bar when upload starts
  document.querySelector("#total-progress").style.opacity = "1";
  // And disable the start button
  file.previewElement.querySelector(".start").setAttribute("disabled", "disabled");
});
 
// Hide the total progress bar when nothing's uploading anymore
myDropzone.on("queuecomplete", function(progress) {
  document.querySelector("#total-progress").style.opacity = "0";
});
 
// Setup the buttons for all transfers
// The "add files" button doesn't need to be setup because the config
// `clickable` has already been specified.
document.querySelector("#actions .start").onclick = function() {
  myDropzone.enqueueFiles(myDropzone.getFilesWithStatus(Dropzone.ADDED));
};
document.querySelector("#actions .cancel").onclick = function() {
  myDropzone.removeAllFiles(true);
};

*/

var dropzone = new Dropzone('#dropzone', {
  parallelUploads: 1,
  maxFilesize: 30,
  filesizeBase: 1000,
  url: "/mdiag/upload",
  acceptedFiles: ".json"
});

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
    $('input[id="jiraid"]').val($('input[id="jira"]').val());
  });
});