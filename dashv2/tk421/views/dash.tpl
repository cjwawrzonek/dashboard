<!DOCTYPE html>
<html lang="en">

<head>

    <script src="./js/jquery.js"></script>
    <script src="./js/jquery.cookie/jquery.cookie.js"></script>
    <script src="./js/bootstrap.min.js"></script>

    <script type="text/javascript" src="./js/dashboard.js"></script>

    <title>Dashboard</title>

    <link rel="shortcut icon" href="/img/mongodb.png" type="image/png" />

    <!-- <link rel="stylesheet" href="/css/bootstrap.min.css"></link> -->
    <link rel="stylesheet" hret="./css/bootstrap-responsive.min.css"></link>

    <!-- Bootstrap Core CSS -->
    <link href="./css/bootstrap.css" rel="stylesheet">

    <!-- Custom CSS -->
    <link rel="stylesheet" href="./css/dashboard.css"></link>
    <link href="./css/sb-admin.css" rel="stylesheet">

</head>

<style>

</style>

<body style="background-color:white" onhashchange="hashHandler()">

    <div id="wrapper">
        <header id="header">
            <div class="container">
                <nav id="primary-navbar">
                    <a  href="dash">
                        <img class="hero-extended" style="position:relative" src="/img/logo.png">
                        <span class="logo-extended" style="font-family:'Trebuchet';text-decoration:none;color:#FFFFFF;font-size:22px;">Greatest Tool </span><span class="logo-extended" style="font-family:'Trebuchet';text-decoration:none;color:#CCCCCC;font-size:22px;">Ever</span>
                    </a>
                    <ul class="list-unstyled menu nav navbar-right top-nav">
                        <li class="header dropdown">
                            <a href="#" class="dropdown-toggle" data-toggle="dropdown"><i class="fa"></i>Alerts <b class="caret"></b></a>
                            <ul class="dropdown-menu message-dropdown usr-alerts">
                            </ul>
                        </li>
                        <li class="header dropdown">
                            <a href="#" class="dropdown-toggle" data-toggle="dropdown"><i class="fa fa-user"></i><span class="dash-user" id="usr_name_space">User Name </span><b class="caret"></b></a>
                            <ul class="dropdown-menu">
                                <li>
                                    <a href="#"><i class="fa fa-fw fa-user"></i> Preferences</a>
                                </li>
                                <li class="divider"></li>
                                <li>
                                    <a onclick="toggleLog()" class="log-link"></i> Log Out</a>
                                </li>
                            </ul>
                        </li>
                    
                    <!-- Sidebar Menu Items - These collapse to the responsive navigation menu on small screens -->
                    <li><button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-ex1-collapse">
                        <span class="sr-only">Toggle navigation</span>
                        <span class="icon-bar" id="toggle-icon"></span>
                        <span class="icon-bar" id="toggle-icon"></span>
                        <span class="icon-bar" id="toggle-icon"></span>
                    </button></li>
                    </ul>
                    <div class="collapse navbar-collapse navbar-ex1-collapse" id="dash-nav">
                        <ul class="nav navbar-nav side-nav">
                            <li class="tcop view">
                                <a href="#Tcop"><i class="fa fa-fw "></i>Traffic Cop</a>
                            </li>
                            <li class="revs view">
                                <a href="#Reviews"><i class="fa fa-fw"></i>Reviews <span style="font-size: 10px;" class="revs-count badge">0</span></a>
                            </li>
                            <li class="unas view">
                                <a href="#Una"><i class="fa fa-fw"></i>Unassigned <span style="font-size: 10px;" class="unas-count badge">0</span></a>
                            </li>
                            <li class="acts view">
                                <a href="#Active"><i class="fa fa-fw"></i>Active <span style="font-size: 10px;" class="acts-count badge">0</span></a>
                            </li>
                            <li class="waits view">
                                <a href="#Waiting"><i class="fa fa-fw"></i>Waiting <span style="font-size: 10px;" class="waits-count badge">0</span></a>
                            </li>
                            <li class="user view">
                                <a href="#User"><span class="dash-user-name dash-user" id="usr_name_space">Dafuq?</span>'s Tickets</a>
                            </li>
                        </ul>
                    </div>
                    <!-- /.navbar-collapse -->
                </nav>
            </div>
        </header>

        <div id="page-wrapper">
            <div class="container-fluid">
                <!-- This is an outer well for displaying errors -->
                <div class="well-sm warning-container hidden" style="background-color:white;">
                </div>

                <!-- Here's the main well for the page, contains each of the data wells  There is a lot of similarity between the dataWells. 
                On my checklist: bottles templating and a little python code to drastically reduce the repetitive HTML code you see below -->
                <div class="well-sm table-container" style="background-color:white;" id="page-well">

                    <div class=" ticketinfo "  style="background-color:white;" id="TCOP">
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

                    <div class=" ticketinfo "  style="background-color:white;" id="TCOP">
                        <div id="FTS"><h3 style="font-size:15;">Follow the Sun <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive" style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                
                    <div class=" ticketinfo "  style="background-color:white;" id="TCOP">
                        <div id="UNA"><h3 style="font-size:15;">Active Unassigned <span style="font-size: 16px;" class="count badge">0</span></h3>
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

                    <div class=" ticketinfo hidden"  style="background-color:white;" id="UNAS">
                        <div id="UNAS"><h3 style="font-size:15;">Active and Waiting Unassigned <span style="font-size: 16px;" class="count badge">0</span></h3>
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

                    <!-- THIS IS NOT CORRECT YET!! Currently, time waiting is time since last customer comment, not last dev comment. Must fix -->
                    <div class=" ticketinfo hidden"  style="background-color:white;" id="WAITING">
                        <div id="WAIT"><h3 style="font-size:15;">Waiting for Customer <span style="font-size: 16px;" class="count badge">0</span></h3>
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


                    <div class=" ticketinfo hidden"  style="background-color:white;" id="USER">
                        <div id="USERASSIGNED"><h3 style="font-size:15;">Open Issues Assigned To <span class="dash-user-name"></span> <span style="font-size: 16px;" class="count badge">0</span></h3>
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

                    <div class=" ticketinfo hidden"  style="background-color:white;" id="USER">
                        <div id="USERREVIEW"><h3 style="font-size:15;">What would you like here <span class="dash-user-name"></span>? <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive" style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th colspan="2">?</th>
                                        <th colspan="2">?</th>
                                        <th colspan="1">?</th>
                                        <th colspan="2">?</th>
                                        <th colspan="5">?</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class=" ticketinfo hidden"  style="background-color:white;" id="USER">
                        <div id="USERREVIEWER"><h3 style="font-size:15;">What would you like here <span class="dash-user-name"></span>? <span style="font-size: 16px;" class="count badge">0</span></h3>
                            <table class="table table-condensed table-hover table-responsive" style="border-collapse:collapse;table-layout:fixed;" id="ticket-tab">
                                <thead>
                                    <tr>
                                        <th colspan="2">?</th>
                                        <th colspan="2">?</th>
                                        <th colspan="1">?</th>
                                        <th colspan="2">?</th>
                                        <th colspan="5">?</th>
                                    </tr>
                                </thead>
                                <tbody class="trows">
                                    <!-- Javascript Inserts Rows Here -->
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div class=" ticketinfo "  style="background-color:white;" id="NOUSER">
                        <div id="NO_USER"><h3 style="font-size:15;">No user logged in. A man needs a name...</h3>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>

</html>
