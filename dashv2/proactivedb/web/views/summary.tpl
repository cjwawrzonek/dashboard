<div id="page-main" class="container">
    % if query is not None:
    <div class="row">
        <div class="col col-lg-12">
            <h3>Results for '{{query}}' ({{count}} total):</h3>
        </div>
    </div>
    % end
    <div class="row">
        <div class="col col-lg-12 text-center">
            <ul class="pagination">
                <%
                prevPage = page - 1
                nextPage = page + 1
                qlink = ''
                if query is not None:
                    qlink = '/%s' % query
                end
                if page == 1:
                %>
                    <li class="disabled"><a class="disabled" href="javascript:void(0);">&larr;</a></li>
                <%
                else:
                %>
                    <li><a href="/groups/{{prevPage}}{{qlink}}">&larr;</a></li>
                <%
                end
                if page > 5:
                %>
                        <li>
                            <a href="/groups/1{{qlink}}">1</a>
                        </li>
                        <li class="disabled">
                            <a class="disabled" href="javascript:void(0);">...</a>
                        </li>
                <%
                end
                for i in range(1,pagesTotal + 2):
                    pClass = ""
                    if i == page:
                        pClass = "active"
                    end
                    if i < (page + 5) and i > (page - 5):
                %>
                    <li class="{{pClass}}">
                        <a class="{{pClass}}" href="/groups/{{i}}{{qlink}}">{{i}}</a>
                    </li>
                <%
                    end
                end
                if pagesTotal - page > 3:
                %>
                        <li class="disabled">
                            <a class="disabled" href="javascript:void(0);">...</a>
                        </li>
                        <li>
                            <a href="/groups/{{pagesTotal + 1}}{{qlink}}">{{pagesTotal + 1}}</a>
                        </li>
                <%
                end
                if page == pagesTotal + 1:
                %>
                    <li class="disabled"><a class="disabled" href="javascript:void(0);">&rarr;</a></li>
                <%
                else:
                %>
                    <li><a href="/groups/{{nextPage}}{{qlink}}">&rarr;</a></li>
                <%
                end
                %>
                </li>
            </ul>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12">
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Customer</th>
                        <th>Failure Count</th>
                        <th>Total Score</th>
                    </tr>
                </thead>
                % for group in groups:
                   <tr>
                       <td><a href="/group/{{group['_id']}}">{{group['name']}}</a></td>
                       <% failedTestsContent = "<div class='col-lg-12'><table class='table'><tr><th>Src</th><th>Test</th><th>Score</th></td>"
                          for test in group['failedTests']:
                            testText = ''.join(["<tr><td>",test['src'],"</td><td>",test['test'],"</td><td>",str(test['score']),"</td></tr>"])
                            if test == issue:
                                testText = ''.join(['<li style="color:#ff0000;"><b>',test,'</b></li>'])
                            end
                            failedTestsContent = failedTestsContent + testText
                         end
                         failedTestsContent = failedTestsContent + "</table></div>"
                       %>
                       <td><span class="failedtests" data-toggle="popover" data-trigger="hover" data-placement="right" data-html="true" title="<b>Failed Tests</b>" data-content="{{failedTestsContent}}">{{len(group['failedTests'])}}</span></td>
                       <td>{{group['score']}}</td>
                   </tr>
                % end
            </table>
        </div>
    </div>
    <div class="row">
        <div class="col col-lg-12 text-center">
            <ul class="pagination">
                <%
                prevPage = page - 1
                nextPage = page + 1
                qlink = ''
                if query is not None:
                    qlink = '/%s' % query
                end
                if page == 1:
                %>
                    <li class="disabled"><a class="disabled" href="javascript:void(0);">&larr;</a></li>
                <%
                else:
                %>
                    <li><a href="/groups/{{prevPage}}{{qlink}}">&larr;</a></li>
                <%
                end
                if page > 5:
                %>
                        <li>
                            <a href="/groups/1{{qlink}}">1</a>
                        </li>
                        <li class="disabled">
                            <a class="disabled" href="javascript:void(0);">...</a>
                        </li>
                <%
                end
                for i in range(1,pagesTotal + 2):
                    pClass = ""
                    if i == page:
                        pClass = "active"
                    end
                    if i < (page + 5) and i > (page - 5):
                %>
                    <li class="{{pClass}}">
                        <a class="{{pClass}}" href="/groups/{{i}}{{qlink}}">{{i}}</a>
                    </li>
                <%
                    end
                end
                if pagesTotal - page > 3:
                %>
                        <li class="disabled">
                            <a class="disabled" href="javascript:void(0);">...</a>
                        </li>
                        <li>
                            <a href="/groups/{{pagesTotal + 1}}{{qlink}}">{{pagesTotal + 1}}</a>
                        </li>
                <%
                end
                if page == pagesTotal + 1:
                %>
                    <li class="disabled"><a class="disabled" href="javascript:void(0);">&rarr;</a></li>
                <%
                else:
                %>
                    <li><a href="/groups/{{nextPage}}{{qlink}}">&rarr;</a></li>
                <%
                end
                %>
                </li>
            </ul>
        </div>
    </div>
</div>
