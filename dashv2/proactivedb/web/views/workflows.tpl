<div id="page-main" class="container">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">Support Issue Workflows</h1>
        </div>
    </div>
    <div class="row">
        <div class="col-md-4 sidebar well" id="sidebar" role="navigation">
            <h4>Existing Workflows</h4>
            <style>
                #page-main ul li, #page-main ol li { padding-bottom: 0px; }
                .nav>li>a { padding: 0px;}
            </style>
            <ul id="existingflows" class="nav">
            </ul>
            <button id="create-btn" class="btn btn-primary col-sm-12">Create Workflow</button>
            <div style="clear:both;"></div>
        </div>
        <div class="col-md-8">
            <form class="form-horizontal" role="form" id="workflow-form" name="workflow-form">
                <input type="hidden" id="workflow._id" name="workflow._id" value=""/>
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <div class="row col-lg-12"><h2>Metadata</h2></div>
                        <div class="form-group">
                            <label for="workflow.name" class="col-sm-2 control-label">Workflow Name</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title editable">
                                    <input type="text" class="form-control" name="workflow.name" id="workflow.name" value="">
                                </h4>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.desc" class="col-sm-2 control-label">Description</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title editable">
                                    <input type="text" class="form-control" name="workflow.desc" id="workflow.desc" value="">
                                </h4>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.owner" class="col-sm-2 control-label">Owner</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title">
                                    <input type="text" class="form-control" name="workflow.owner" id="workflow.owner" value="">
                                </h4>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.groups" class="col-sm-2 control-label">Groups</label>
                            <div class="col-sm-10">
                                <h4 class="panel-title editable">
                                    <input type="text" class="form-control" name="workflow.groups" id="workflow.groups" value="">
                                </h4>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.public" class="col-sm-2 control-label">Public</label>
                            <div class="col-sm-10">
                                <input type="hidden" name="workflow.public" value="false">
                                <input type="checkbox" class="form-control input-sm" name="workflow.public" id="workflow.public" value="true">
                            </div>
                        </div>
                    </div>
                    <div class="panel-body">
                        <div class="row col-lg-12"><h2>Filtering</h2></div>
                        <div class="form-group">
                            <label for="workflow.auto_approve" class="col-sm-2 control-label">Auto approve</label>
                            <div class="col-sm-10">
                                <input type="hidden" name="workflow.auto_approve" value="false">
                                <input type="checkbox" class="form-control input-sm" name="workflow.auto_approve" id="workflow.auto_approve" value="true">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="prereqs" class="col-sm-2 control-label">Prerequisites</label>
                            <div class="col-sm-10">
                                <table class="table table table-condensed table-bordered">
                                    <thead>
                                        <tr>
                                            <th class="col-sm-1"><i class="glyphicon glyphicon-cog"></i></th>
                                            <th class="col-sm-6">Name</th>
                                            <th class="col-sm-5">Time Elapsed</th>
                                        </tr>
                                    </thead>
                                    <tbody id="prereqsList">
                                        <tr id="addPrereq-link">
                                            <td colspan="3">
                                                <a id="add-prereq-btn" href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Prerequisite">
                                                    <i class="glyphicon glyphicon-plus"></i>
                                                </a>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.ns" class="col-sm-2 control-label">Namespace 1 (Primary)</label>
                            <div class="col-sm-10">
                                <select type="hidden" id="workflow.ns" name="workflow.ns" class="form-control input-sm">
                                    <%
                                    for db in databases:
                                        if len(databases[db]) > 0:
                                    %>
                                            <optgroup label="{{db}}">
                                            <%
                                            for coll in databases[db]:
                                            %>
                                                <option value="{{db}}.{{coll}}">{{coll}}</option>
                                            <%
                                            end
                                        end
                                    end
                                    %>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.join_key" class="col-sm-2 control-label">Join Key 1</label>
                            <div class="col-sm-10">
                                <input id="workflow.join_key" name="workflow.join_key" class="form-control input-sm" value="">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.query_string" class="col-sm-2 control-label">Query String 1</label>
                            <div class="col-sm-10">
                                <textarea id="workflow.query_string" name="workflow.query_string" class="form-control input-sm" rows="10"></textarea>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.ns1" class="col-sm-2 control-label">Namespace 2</label>
                            <div class="col-sm-10">
                                <select type="hidden" id="workflow.ns1" name="workflow.ns1" class="form-control input-sm">
                                    <%
                                    for db in databases:
                                        if len(databases[db]) > 0:
                                    %>
                                            <optgroup label="{{db}}">
                                            <%
                                            for coll in databases[db]:
                                            %>
                                                <option value="{{db}}.{{coll}}">{{coll}}</option>
                                            <%
                                            end
                                        end
                                    end
                                    %>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.join_key1" class="col-sm-2 control-label">Join Key 2</label>
                            <div class="col-sm-10">
                                <input id="workflow.join_key1" name="workflow.join_key1" class="form-control input-sm" value="">
                            </div>
                        </div>
                        <div class="form-group">
                            <label for="workflow.query_string1" class="col-sm-2 control-label">Query String 2</label>
                            <div class="col-sm-10">
                                <textarea id="workflow.query_string1" name="workflow.query_string1" class="form-control input-sm" rows="10"></textarea>
                            </div>
                        </div>
                        <div class="row col-lg-12"><h2>Actions</h2></div>
                        <div class="form-group">
                            <div class="col-sm-12">
                                <table class="table table table-condensed table-bordered">
                                    <thead>
                                        <tr>
                                            <th class="col-sm-3">Name</th>
                                            <th class="col-sm-9">Args</th>
                                        </tr>
                                    </thead>
                                    <tbody id="actionsList">
                                        <tr id="addAction-link">
                                            <td colspan="2">
                                                <a id="add-action-btn" href="javascript:void(0);" data-toggle="tooltip" data-placement="top" title="Add Action">
                                                    <i class="glyphicon glyphicon-plus"></i>
                                                </a>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                    <div class="btn-group pull-right">
                        <button id="test-workflow-link" type="button" class="btn btn-warning ladda-button" data-style="slide-left"><span class="ladda-label">Test Workflow&nbsp;<i class="glyphicon glyphicon-cog"></i></span></button>
                        <button id="save-link" type="button" class="btn btn-primary ladda-button" data-style="slide-left"><span class="ladda-label">Save Workflow&nbsp;<i class="glyphicon glyphicon-cloud-upload"></i></span></button>
                        <button type="button" class="btn btn-primary dropdown-toggle" data-toggle="dropdown">
                            <span class="caret"></span>
                            <span class="sr-only">Toggle Dropdown</span>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-right" role="menu">
                            <li><a id="save-copy-link" href="javascript:void(0);">Save as New Workflow</a></li>
                        </ul>
                    </div>
                </div>
            </form>
        </div>
    </div>
    <div class="row" style="height:40px;"><div class="col-sm-12"></div></div>
    <div class="row">
        <div id="test-workflow-form" class="col-lg-10 col-md-10 col-lg-offset-2 col-md-offset-2" style="display:none">
            <div class="panel-group" id="accordion">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 class="panel-title">
                            <span>Test Results</span>
                            <div class="pull-right">
                                <button id="test-workflow-close" type="button" class="close"><span aria-hidden="true">&times;</span><span class="sr-only">Close</span></button>
                            </div>
                        </h4>
                        <div style="clear:both"></div>
                    </div>
                    <div class="panel-body">
                        <h4>Test Summary</h4>
                        <div id="test-workflow-summary"></div>
                        <h4>Matching Documents</h4>
                        <div id="test-workflow-results"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
