<div id="page-main" class="container">
    <div class="row">
        <div class="col col-lg-12">
            <h1 class="page-header">MDiag Processor</h1>
        </div>
    </div>
    <div class="row">
        <div class="col-md-12">
            <div class="panel panel-default">
                <div class="panel-heading">
                    <h2>Metadata</h2>
                    <div class="row form-group">
                        <label for="jiraid" class="col-sm-2 control-label">JIRA Ticket</label>
                        <div class="col-sm-10">
                            <h4 class="panel-title editable">
                                <input type="text" class="form-control" name="jira" id="jira" value="">
                            </h4>
                        </div>
                        <label for="customer" class="col-sm-2 control-label">Customer</label>
                        <div class="col-sm-10">
                            <h4 class="panel-title editable">
                                <input type="text" class="form-control" disabled="disabled" name="customer" id="customer" value="">
                            </h4>
                        </div>
                    </div>
                </div>
                <div class="panel-body">
                    <div class="row col-lg-12"><h2>Upload mdiag JSON</h2></div>
                    <div class="row col-lg-12">
                        <form class="form-horizontal dropzone" role="form" id="workflow-form" name="workflow-form">
                            <div id="dropzone" style="border: 2px dashed;">
                                <input type="hidden" name="jiraid" id="jiraid" value=""/>
                                <div class="dz-message">Drop file here or click to upload.</div>
                            </div>
                        </form>
                    </div>
                </div>
                <div class="btn-group pull-right">
                    <button id="test-workflow-link" type="button" class="btn btn-warning ladda-button" data-style="slide-left"><span class="ladda-label">Run Tests&nbsp;<i class="glyphicon glyphicon-cog"></i></span></button>
                </div>
            </div>
            <div class="row col-lg-12"><br/><br/></div>
            <div id="resultsPanel" class="panel panel-default" style="display:none;">
                <div class="panel-heading">
                    <div class="row col-lg-12"><h2>Results</h2></div>
                </div>
                <div class="panel-body">
                    <div class="form-group">
                        <div class="col-sm-12">
                            <table class="table table table-condensed table-bordered">
                                <thead>
                                    <tr>
                                        <th class="col-sm-3">Test</th>
                                        <th class="col-sm-9">Result</th>
                                    </tr>
                                </thead>
                                <tbody id="resultsList">
                                    <tr>
                                        <td>Test 1</td>
                                        <td>Pass</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
