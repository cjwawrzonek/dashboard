<!DOCTYPE html>

<html lang="en">
    % include('head.tpl')
    <body id="bv1">
        <%
        include('nav.tpl')
        if defined('error'):
            include('error.tpl')
        elif defined('renderpage'):
            include(renderpage)
        end
        include('footer.tpl')
        %>
    </body>
</html>
