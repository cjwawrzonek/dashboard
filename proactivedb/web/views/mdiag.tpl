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
                    <h2>1. Metadata</h2>
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
                <div class="panel-body" id="uploadPanel" style="display:none;">
                    <div class="row col-lg-12"><h2>2. Upload mdiag JSON</h2></div>
                    <div class="row col-lg-12">
                        <form class="form-horizontal dropzone" role="form" id="workflow-form" name="workflow-form">
                            <div id="dropzone" style="border: 2px dashed;">
                                <div class="dz-message">Drop file here or click to browse files.</div>
                            </div>
                        </form>
                    </div>
                </div>
                <div id="submitPanel" name="submitPanel" class="btn-group pull-right" style="display:none;">
                    <button id="test-mdiag-btn" type="submit" class="btn btn-warning ladda-button" data-style="slide-left"><span class="ladda-label">Upload MDiag file and Run Tests&nbsp;<i class="glyphicon glyphicon-cog"></i></span></button>
                </div>
            </div>
            <div class="row col-lg-12"><br/><br/></div>
        </div>
    </div>
    <div class="row">
        <div class="col-md-12">
            <div id="resultsPanel" class="panel panel-default" style="display:none;">
                <div class="panel-heading">
                    <h2>3. Results</h2>
                </div>
                <div class="panel-body">
                    <table class="table table table-condensed table-bordered">
                        <thead>
                            <tr>
                                <th class="col-sm-3">Test</th>
                                <th class="col-sm-8">Description</th>
                                <th class="col-sm-1">Result</th>
                            </tr>
                        </thead>
                        <tbody id="resultsTableBody">
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</div>
