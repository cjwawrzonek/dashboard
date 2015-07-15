<div class="container-fluid">
    <div class="row">
        <div class="col col-lg-12" style="margin-bottom:1em">
            <table class="table table-striped">
                <tr>
                    <td>
                        <!--span class="h1">Support Issue Workflows</span-->
                        <span id="selectWorkflowsDropdown" class="dropdown">
                            <a href="javascript:void(0)" id="a_selectWorkflowsDropdown" data-toggle="dropdown">
                                <i id="i_dropdown" class="glyphicon glyphicon-plus"></i> Add/Remove Workflows
                            </a>
                            <ul class="dropdown-menu dropdown-menu-left" role="menu" aria-labelledby="a_selectWorkflowsDropdown" style="width:300px;">
                                <%
                                  wfkeys = allWorkflows.keys()
                                  for wfindex in wfkeys:
                                        workflow = allWorkflows[wfindex]
                                        workflowId = workflow['name'].replace(" ", "_")
                                %>
                                <li style="margin-left:10px">
                                    <input id="checkbox_{{workflowId}}" class="selectWorkflowsDropdownCheckbox" type="checkbox" value="{{workflow['name']}}"> {{workflow['name']}}
                                </li>
                                % end
                            </ul>
                        </span>
                    </td>
                </tr>
            </table>
        </div>
    </div>
    <div class="row">
        <div id="ticketList" class="col-lg-12" style="width:50%">
            <div class="panel-group" id="accordion">
                {{! content}}
            </div>
        </div>
        <div id="ticketContent" style="display:none; position:absolute; right:10px">
            <div class="panel-group" id="accordion">
                <div class="panel panel-default">
                    <div class="panel-heading">
                        <h4 id="ticketTitle" class="panel-title">
                            <span></span>
                            <div class="pull-right">
                                <a target="_blank" id="ticketLink" href=""><i class="glyphicon glyphicon-share"></i></a>
                                <a href="javascript:void(0);" onclick="closePage();"><i class="glyphicon glyphicon-remove"></i></a>
                            </div>
                        </h4>
                        <div style="clear:both"></div>
                    </div>
                    <div class="panel-body">
                        <iframe src="" id="ticketFrame"></iframe>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
