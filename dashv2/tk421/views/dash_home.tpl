<!DOCTYPE html>
<html lang="en">
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
    <script src="./js/spin.min.js"></script>
    <script src="./js/moment.min.js"></script>
    <!-- <script src="http://code.jquery.com/ui/1.9.2/jquery-ui.js"></script> -->
    <!-- <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/js/bootstrap.min.js"></script> -->
    <link rel="shortcut icon" href="https://cdn.rawgit.com/dtgm/chocolatey-packages/8f7101024b11677be45a74b45114000b428a9c9b/icons/mongodb.png" type="image/png" />
    <link rel="stylesheet" href="./css/bootstrap.min.css"></link>
    <link rel="stylesheet" href="./css/dashboard.css"></link>
    <link rel="stylesheet" hret="./css/bootstrap-responsive.min.css"></link>

    <body style="background-color:#3b291f;" onhashchange="hashHandler()">
        <div class="container-fluid">
            <div class="well row-fluid" style="background-color:white;" id="HEAD">
                <!-- <div class="row col-lg-12"> -->
                    <ul class="nav nav-pills">
                        <li style="width:30%;font-size:20px;"><a href="#Tickets">Tickets</a></li>
                        <li style="width:30%;font-size:20px;"><a href="#Reviews">Reviews</a></li>
                    </ul>
                <!-- </div> -->
            </div>

            <div class="well" style="background-color:white;">
                <div class=" ticketinfo col-lg-6"  style="background-color:white;" id="TICKS">
                    <div id="SLA"><h3 style="font-size:15;">SLA Tickets</h3>
                        <table class="table table-condensed" style="border-collapse:collapse;" id="ticket-tab">
                            <thead>
                                <tr>
                                    <th>Ticket ID</th>
                                    <th>SLA Time</th>
                                    <th>Priority</th>
                                    <th>Assignee</th>
                                    <th>Description</th>
                                </tr>
                            </thead>
                            <tbody class="trows">
                                <!-- Javascript Inserts Rows Here -->
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class=" ticketinfo col-lg-6"  style="background-color:white;" id="TICKS">
                    <div id="FTS"><h3 style="font-size:15;">FTS Tickets</h3>
                        <table class="table table-condensed" style="border-collapse:collapse;" id="ticket-tab">
                            <thead>
                                <tr>
                                    <th>Ticket ID</th>
                                    <th>FTS Time</th>
                                    <th>Priority</th>
                                    <th>Some Field</th>
                                    <th>Other Field</th>
                                </tr>
                            </thead>
                            <tbody class="trows">
                                <!-- Javascript Inserts Rows Here -->
                            </tbody>
                        </table>
                    </div>
                </div>
            <!-- </div> -->

                <div class="row-fluid">
                    <div class=" ticketinfo col-large-6"  style="background-color:white;" id="TICKS">
                        <div id="UNA"><h3 style="font-size:15;">UNA Tickets</h3>
                            <table class="table table-condensed" style="border-collapse:collapse;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th>Ticket ID</th>
                                        <th>UNA Time</th>
                                        <th>Priority</th>
                                        <th>Some Field</th>
                                        <th>Other Field</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class=" ticketinfo hidden"  style="background-color:white;" id="REVS">
                        <div id="REV"><h3 style="font-size:15;">Reviews</h3>
                            <table class="table table-condensed" style="border-collapse:collapse;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th>Ticket ID</th>
                                        <th>Review Time</th>
                                        <th>Priority</th>
                                        <th>Requested By</th>
                                        <th>Some Field</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class=" ticketinfo col-large-6"  style="background-color:white;" id="TICKS">
                        <div id="ACTS"><h3 style="font-size:15;">Remaining Active Tickets</h3>
                            <table class="table table-condensed" style="border-collapse:collapse;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th>Ticket ID</th>
                                        <th>Time Waiting</th>
                                        <th>Priority</th>
                                        <th>Assignee</th>
                                        <th>Other Field</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    <script type="text/javascript" src="./js/dashboard.js"></script>
</html>