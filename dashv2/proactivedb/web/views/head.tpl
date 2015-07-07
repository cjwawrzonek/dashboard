<head>
    % if defined('renderpage') and renderpage != 'summary':
    <title>{{renderpage}} | proactiveDB</title>
    % else:
    <title>Home | proactiveDB</title>
    % end
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
    <link rel="stylesheet" media="all" href="/css/application.css"/>
    <link rel="stylesheet" href="/css/ladda-themeless.min.css"/>
    <link rel="stylesheet" href="/css/app.css"/>
    <link rel="stylesheet" href="/css/prettify.css"/>
    <link rel="stylesheet" href="/css/select2.min.css"/>
    <link rel="stylesheet" href="/css/dropzone.css"/>
    <link rel="icon" href="/img/favicon.ico" type="image/x-icon">
    <link rel="shortcut icon" href="/img/favicon.ico" type="image/x-icon">
    % if defined('renderpage'):
    <link rel="stylesheet" href="/css/{{renderpage}}.css"/>
    % end
</head>