<!DOCTYPE html>
<html lang="en">
	<head>
		<title>Support Dashboard</title>
		<meta content="text/html;charset=utf-8" http-equiv="Content-Type">
		<meta content="utf-8" http-equiv="encoding">
		<meta name="viewport" content="width=device-width, initial-scale=1.0">
		<script src="./js/jquery-2.1.1.min.js"></script>
		<script src="./js/moment.min.js"></script>
		<script src="./js/spin.min.js"></script>
    <link rel="stylesheet" href="./css/bootstrap.min.css"></link>
    <link rel="stylesheet" href="./css/dashboard.css"></link>
	</head>
	<body>
    <div id="outer-div" class="col-lg-12">
      <h1 id="dash-header" class="page-header">Support Dashboard
          <span class="pull-right">
              <div id="current-container">Current time: <span id="currently"></span></div>
              <div id="updated-container" class="priority danger">Last updated <span id="last-updated"></span> seconds ago</div>
          </span>
      </h1>
    </div>
    <div id="warning-container" class="alert alert-info">
      <h1>Loading...</h1>
    </div>
    <div id="table-container" class="container-fluid hidden">
      <div class="row" id="SLA">
        <div class="col-lg-1">
          <h1>SLA<br/><span class="count label">!COUNT</span></h1>
        </div>
        <div class="col-lg-11">
          <ul class="list-inline tickets">
          </ul>
        </div>
      </div>
      <div class="row" id="FTS">
        <div class="col-lg-1">
          <h1>FTS<br/><span class="count label">!COUNT</span></h1>
        </div>
        <div class="col-lg-11">
          <ul class="list-inline tickets">
          </ul>
        </div>
      </div>
      <div class="row" id="REV">
        <div class="col-lg-1">
          <h1>REV<br/><span class="count label">!COUNT</span></h1>
        </div>
        <div class="col-lg-11">
          <ul class="list-inline tickets">
          </ul>
        </div>
      </div>
      <div class="row" id="UNA">
        <div class="col-lg-1">
          <h1>UNA<br/><span class="count label label-info">!COUNT</span></h1>
        </div>
        <div class="col-lg-11">
          <ul class="list-inline tickets">
          </ul>
        </div>
      </div>
      <div class="row" id="totals">
        <div class="col-lg-3"><h1>Active: <span class='total' id='active'>!TOTAL</span></h1></div>
        <div class="col-lg-3"><h1>Waiting: <span class='total' id='waiting'>!TOTAL</span></h1></div>
        <div class="col-lg-3"><h1>Total: <span class='total' id='total'>!TOTAL</span></h1></div>
        <div class="col-lg-1"><h1>Show:</h1></div>
        <div class="col-lg-2">
            <table class="table legend">
                <tr>
                    <td>
                        <h4><input id="show-assignee" type="checkbox" checked="true"> Assignee</h4>
                        <h4><input id="show-low-priorities" type="checkbox" checked="true"> Low Priorities</h4>
                    </td>
                </tr>
                <!--
                <tr>
                    <td>
                        <h4 class="glyphicon glyphicon-arrow-up priority warning">P3</h4>
                    </td>
                    <td>
                        <h4 class="glyphicon glyphicon-arrow-down priority success">P4/P5</h4>
                    </td>
                </tr>
                -->
            </table>
        </div>
      </div>
    </div>
		<script type="text/javascript" src="./js/dashboard.js"></script>
	</body>
</html>

