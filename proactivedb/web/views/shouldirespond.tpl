<div id="page-main" class="container">
    <div class="row">
        <div class="col-lg-12">
            <h2>A ticket came in, should I respond?</h2>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12">
            <div id="decisionPanel" class="panel panel-default">
                <div class="panel-heading">
                    <h4>Decision Workflow</h4>
                </div>
                <div class="panel-body">
                    <div id="divLocation" class="row">
                        <label for="selLocation" class="col-sm-3 control-label">Where are you?</label>
                        <div class="col-sm-9">
                            <select id="selLocation">
                                <option value=""></option>
                                <option value="Austin">Austin</option>
                                <option value="Dublin">Dublin</option>
                                <option value="New York">New York</option>
                                <option value="Palo Alto">Palo Alto</option>
                                <option value="Sydney">Sydney</option>
                                <option value="Tel Aviv">Tel Aviv</option>
                            </select>
                        </div>
                    </div>
                    <div id="divDay" class="row" style="display:none;">
                        <label for="selDay" class="col-sm-3 control-label">What day is it?</label>
                        <div class="col-sm-9">
                            <select id="selDay">
                                <option value=""></option>
                                <option value="Monday">Monday</option>
                                <option value="Tuesday">Tuesday</option>
                                <option value="Wednesday">Wednesday</option>
                                <option value="Thursday">Thursday</option>
                                <option value="Friday">Friday</option>
                                <option value="Saturday">Saturday</option>
                                <option value="Sunday">Sunday</option>
                            </select>
                        </div>
                    </div>
                    <div id="divWR" class="row" style="display:none;">
                        <label for="selWR" class="col-sm-3 control-label">Are you Weekend Responder?</label>
                        <div class="col-sm-9">
                            <select id="selWR">
                                <option value=""></option>
                                <option value="yes">yes</option>
                                <option value="no">no</option>
                            </select>
                        </div>
                    </div>
                    <div id="divPriority" class="row" style="display:none;">
                        <label for="selPriority" class="col-sm-3 control-label">What priority is the ticket?</label>
                        <div class="col-sm-9">
                            <select id="selPriority">
                                <option value=""></option>
                                <option value="P1">P1</option>
                                <option value="P2">P2</option>
                                <option value="P3">P3</option>
                                <option value="P4">P4</option>
                                <option value="P5">P5</option>
                            </select>
                        </div>
                    </div>
                </div>
                <div class="panel-footer">
                    <div class="row">
                        <div id="decisionType" class="alert alert-success col-lg-12" style="display:none;">
                            <h4 id="decision">Yes!</h4>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
