<div id="page-main" class="container">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Group Tests</h1>
        </div>
    </div>
    <div class="row">
        <div class="col-md-4 sidebar well" id="sidebar" role="navigation">
            <h4>Existing Tests</h4>
            <style>
                #page-main ul li, #page-main ol li { padding-bottom: 0px; }
                .nav>li>a { padding: 0px;}
            </style>
            <ul id="existingtests" class="nav">
            </ul>
            <button id="create-btn" class="btn btn-primary col-sm-12">Create Test</button>
            <div style="clear:both;"></div>
        </div>
        <div class="col-md-8">
            <div class="alert" id="test-exists" style="display:none;"></div>
            <form class="form-horizontal" role="form" id="test-form" name="test-form">
                <input type="hidden" id="test._id" name="test._id" value=""/>
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <div class="form-group">
                            <label for="test.name" class="col-sm-2 control-label">Test Name</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title editable">
                                    <input type="text" class="form-control" name="test.name" id="test.name" value="">
                                </h4>
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="form-group">
                            <label for="test.active" class="col-sm-2 control-label">Active</label>
                            <div class="col-sm-10">
                                <input type="checkbox" class="form-control input-sm" name="test.active" id="test.active" value="">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="test.src" class="col-sm-2 control-label">Source</label>
                            <div class="col-sm-10">
                                <select class="form-control input-sm" name="test.src" id="test.src" value="">
                                    <option value="pings">pings</option>
                                    <option value="mdiags">mdiags</option>
                                    <option value="mmsgroupreports">mmsgroupreports</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="test.collections" class="col-sm-2 control-label">Collections</label>
                            <div class="col-sm-10">
                                <select class="form-control input-sm" multiple="true" name="test.collections" id="test.collections"></select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="test.priority" class="col-sm-2 control-label">Priority</label>
                            <div class="col-sm-10">
                                <select class="form-control input-sm" name="test.priority" id="test.priority" value="">
                                    <option value="low">low</option>
                                    <option value="medium">medium</option>
                                    <option value="high">high</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="test.header" class="col-sm-2 control-label">Header</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title editable">
                                    <input type="text" class="form-control" name="test.header" id="test.header" value="">
                                </h4>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="test.comment" class="col-sm-2 control-label">Comment</label>
                            <div class="col-sm-10">
                                <textarea id="test.comment" name="test.comment" class="form-control input-sm" rows="10"></textarea>
                            </div>
                        </div>
                    </div>
                    <div class="btn-group pull-right">
                        <button id="test-link" type="button" class="btn btn-warning ladda-button" data-style="slide-left"><span class="ladda-label">Test&nbsp;<i class="glyphicon glyphicon-cog"></i></span></button>
                        <button id="save-link" type="button" class="btn btn-primary ladda-button" data-style="slide-left"><span class="ladda-label">Save Test&nbsp;<i class="glyphicon glyphicon-cloud-upload"></i></span></button>
                        <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown">
                            <span class="caret"></span>
                            <span class="sr-only">Toggle Dropdown</span>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-right" role="menu">
                            <li><a id="save-copy-link" href="javascript:void(0);">Save as New Test</a></li>
                        </ul>
                    </div>
                </div>
            </form>
            <br/>
            <br/>
            <div id="test-result-form" class="panel panel-primary" style="display:none">
                <div class="panel-heading">
                    <h4 class="panel-title">
                        <span>Test Results</span>
                        <div class="pull-right">
                            <button id="test-close" type="button" class="close"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
                        </div>
                    </h4>
                    <div style="clear:both"></div>
                </div>
                <div class="panel-body">
                    <h4>Matching Groups</h4>
                    <table class="table table-striped">
                        <thead>
                            <tr>
                                <th>Group Name</th>
                                <th>Priority Score</th>
                                <th>Customer Last Login</th>
                                <th>Last Agent Ping</th>
                            </tr>
                        </thead>
                        <tbody id="test-results">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    <div class="row" style="height:40px;"><div class="col-sm-12"></div></div>
    <div class="row">

    </div>
</div>