<!DOCTYPE html>
<html lang="en">

<head>

    <script src="./js/jquery.js"></script>
    <script src="./js/bootstrap.min.js"></script>

    <script type="text/javascript" src="./js/dashboard.js"></script>

    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="description" content="">
    <meta name="author" content="">

    <title>Dashboard</title>

    <link rel="shortcut icon" href="https://cdn.rawgit.com/dtgm/chocolatey-packages/8f7101024b11677be45a74b45114000b428a9c9b/icons/mongodb.png" type="image/png" />

    <!-- <link rel="stylesheet" href="/css/bootstrap.min.css"></link> -->
    <link rel="stylesheet" href="./css/dashboard.css"></link>
    <link rel="stylesheet" hret="./css/bootstrap-responsive.min.css"></link>

    <!-- Bootstrap Core CSS -->
    <link href="./css/bootstrap.css" rel="stylesheet">

    <!-- Custom CSS -->
    <link href="./css/sb-admin.css" rel="stylesheet">

    <!-- Custom Fonts -->
    <link rel="./font-awesome/css/font-awesome.min.css" rel="stylesheet" type="text/css">

</head>

<body style="background-color:#3b291f;" onhashchange="hashHandler()">

    <div id="wrapper">

        <!-- Navigation -->
        <nav class="navbar navbar-inverse navbar-fixed-top" role="navigation">
            <!-- Brand and toggle get grouped for better mobile display -->
            <div class="navbar-header">
                <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
                    <span class="sr-only">Toggle navigation</span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                </button>
                <a class=" navbar-brand" href="dash" >
                <img class="media-object" style="max-width:140%;max-height:140%;float: right;" src="/img/MongoDB_Logo.png" type="image/png"alt="No Image: "></a>
            </div>
            <!-- Top Menu Items -->
            <ul class="nav navbar-left top-nav">
                <a href="" class="navbar-brand">Support Dashboard</a>
            </ul>
            <ul class="nav navbar-right top-nav">
                <li class="dropdown">
                    <a href="#" class="dropdown-toggle" data-toggle="dropdown"><i class="fa"></i>Alerts <b class="caret"></b></a>
                    <ul class="dropdown-menu message-dropdown">
                        <li class="message-preview">
                            <a href="#">
                                <div class="media">
                                    <span class="pull-left">
                                        <!-- <img class="media-object" src="http://placehold.it/50x50" alt=""> -->
                                    </span>
                                    <div class="media-body">
                                        <h5 class="media-heading"><strong>Christian W</strong>
                                        </h5>
                                        <p class="small text-muted"><i class="fa fa-clock-o"></i> Today at 1:00 PM</p>
                                        <p>Ticket CS-12345 was assigned to you.</p>
                                    </div>
                                </div>
                            </a>
                        </li>
                        <li class="message-preview">
                            <a href="#">
                                <div class="media">
                                    <span class="pull-left">
                                        <!-- <img class="media-object" src="http://placehold.it/50x50" alt=""> -->
                                    </span>
                                    <div class="media-body">
                                        <h5 class="media-heading"><strong>Christan W</strong>
                                        </h5>
                                        <p class="small text-muted"><i class="fa fa-clock-o"></i> Yesterday at 4:32 PM</p>
                                        <p>Nick gave CS-74938 an LGTM</p>
                                    </div>
                                </div>
                            </a>
                        </li>
                        <li class="message-preview">
                            <a href="#">
                                <div class="media">
                                    <span class="pull-left">
                                        <!-- <img class="media-object" src="http://placehold.it/50x50" alt=""> -->
                                    </span>
                                    <div class="media-body">
                                        <h5 class="media-heading"><strong>Christian W</strong>
                                        </h5>
                                        <p class="small text-muted"><i class="fa fa-clock-o"></i> Yesterday at 4:00 PM</p>
                                        <p>Ticket CS-54321 is about to expire!</p>
                                    </div>
                                </div>
                            </a>
                        </li>
                        <li class="message-footer">
                            <a href="#">Read All New Messages</a>
                        </li>
                    </ul>
                </li>

                <li class="dropdown">
                    <a href="#" class="dropdown-toggle" data-toggle="dropdown"><i class="fa fa-user"></i> User Name <b class="caret"></b></a>
                    <ul class="dropdown-menu">
                        <li>
                            <a href="#"><i class="fa fa-fw fa-user"></i> Preferences</a>
                        </li>
                        <li class="divider"></li>
                        <li>
                            <a href="#"><i class="fa fa-fw fa-power-off"></i> Log Out</a>
                        </li>
                    </ul>
                </li>
            </ul>
            <!-- Sidebar Menu Items - These collapse to the responsive navigation menu on small screens -->
            <div class="collapse navbar-collapse navbar-ex1-collapse">
                <ul class="nav navbar-nav side-nav">
                    <li>
                        <a href="#Tickets"><i class="fa fa-fw"></i>Traffic Cop</a>
                    </li>
                    <li>
                        <a href="#Reviews"><i class="fa fa-fw"></i>Reviews</a>
                    </li>
                    <li>
                        <a href="#Active"><i class="fa fa-fw"></i>All Active</a>
                    </li>
                    <li>
                        <a href="#Users"><i class="fa fa-fw"></i>#Name#'s Tickets</a>
                    </li>
                    <li>
                        <a href="#Waiting"><i class="fa fa-fw"></i>Waiting</a>
                    </li>
                </ul>
            </div>
            <!-- /.navbar-collapse -->
        </nav>

        <div id="page-wrapper" style="background-color:#3b291f;">

            <div class="container-fluid">

<!--             <div class="well row-fluid" style="background-color:white;" id="HEAD">
                    <ul class="nav nav-pills">
                        <li style="width:30%;font-size:20px;"><a href="#Tickets">Tickets</a></li>
                        <li style="width:30%;font-size:20px;"><a href="#Reviews">Reviews</a></li>
                    </ul>
            </div> -->


                <div class="well-sm" style="background-color:white;">
                <!-- <div class="row-fluid"> -->
                    <div class=" ticketinfo "  style="background-color:white;" id="TICKS">
                        <div id="SLA"><h3 style="font-size:15;">Active SLAs <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive " style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th colspan="2">Ticket ID</th>
                                        <th colspan="2">Time Remaining</th>
                                        <th colspan="1">Priority</th>
                                        <th colspan="2">Assignee</th>
                                        <th colspan="5">Description</th>
                                    </tr>
                                </thead>
                                <tbody class="trows ">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class=" ticketinfo "  style="background-color:white;" id="TICKS">
                        <div id="FTS"><h3 style="font-size:15;">Follow the Sun <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive" style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th colspan="2">Ticket ID</th>
                                        <th colspan="2">Time Waiting</th>
                                        <th colspan="1">Priority</th>
                                        <th colspan="2">Assignee</th>
                                        <th colspan="5">Description</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                <!-- </div> -->

                
                    <div class=" ticketinfo "  style="background-color:white;" id="TICKS">
                        <div id="UNA"><h3 style="font-size:15;">Unassigned Tickets <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive" style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th colspan="2">Ticket ID</th>
                                        <th colspan="2">Time Waiting</th>
                                        <th colspan="1">Priority</th>
                                        <th colspan="2">Assignee</th>
                                        <th colspan="5">Description</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class=" ticketinfo hidden"  style="background-color:white;" id="REVS">
                        <div id="REV"><h3 style="font-size:15;">Reviews <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive" style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th>Ticket ID</th>
                                        <th>Time Waiting</th>
                                        <th>Requested By</th>
                                        <th>Reviewers</th>
                                        <th>LGTMs</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class=" ticketinfo hidden"  style="background-color:white;" id="ACTIVE">
                        <div id="ACTS"><h3 style="font-size:15;">All Active Tickets <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive" style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th colspan="2">Ticket ID</th>
                                        <th colspan="2">Time Waiting</th>
                                        <th colspan="1">Priority</th>
                                        <th colspan="2">Assignee</th>
                                        <th colspan="5">Description</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            <!-- </div> -->

                <!-- Page Heading -->
                <!-- /.row -->
                <!-- /.row -->

            </div>
            <!-- /.container-fluid -->

        </div>
        <!-- /#page-wrapper -->

    </div>
    <!-- /#wrapper -->

    <!-- jQuery -->
    <!-- // <script src="js/jquery.js"></script> -->

    <!-- Bootstrap Core JavaScript -->

    <!-- Morris Charts JavaScript -->
<!--     // <script src="js/plugins/morris/raphael.min.js"></script>
    // <script src="js/plugins/morris/morris.min.js"></script>
    // <script src="js/plugins/morris/morris-data.js"></script> -->

</body>

</html>
