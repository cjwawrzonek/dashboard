<header id="header">
    <div class="container">
        <nav id="primary-navbar">
            <a href="/">
                <img class="hero-extended" style="position:relative" src="/img/logo.png"/>
                <img class="hero-condensed" style="position:absolute" src="/img/logo.png"/>
                <span class="logo-extended" style="font-family:'Trebuchet';text-decoration:none;color:#FFFFFF;font-size:22px;">proactive</span><span class="logo-extended" style="font-family:'Trebuchet';text-decoration:none;color:#CCCCCC;font-size:22px;">DB</span>
            </a>
            <ul class="list-unstyled menu">
                <%
                for section in ["groups","tests","mdiag","workflows","tasks"]:
                    active = ""
                    if section == renderpage:
                        active = "active"
                    end
                %>
                    <li class="header"><a href="/{{section}}" class="{{active}}">{{section}}</a></li>
                % end
                <li class="svg search input-search">
                    <div class="border"></div>
                    <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="16" height="16" viewBox="0 0 24 24">
                        <path fill="#fff" d="M10 1q1.828 0 3.496 0.715t2.871 1.918 1.918 2.871 0.715 3.496q0 1.57-0.512 3.008t-1.457 2.609l5.68 5.672q0.289 0.289 0.289 0.711 0 0.43-0.285 0.715t-0.715 0.285q-0.422 0-0.711-0.289l-5.672-5.68q-1.172 0.945-2.609 1.457t-3.008 0.512q-1.828 0-3.496-0.715t-2.871-1.918-1.918-2.871-0.715-3.496 0.715-3.496 1.918-2.871 2.871-1.918 3.496-0.715zM10 3q-1.422 0-2.719 0.555t-2.234 1.492-1.492 2.234-0.555 2.719 0.555 2.719 1.492 2.234 2.234 1.492 2.719 0.555 2.719-0.555 2.234-1.492 1.492-2.234 0.555-2.719-0.555-2.719-1.492-2.234-2.234-1.492-2.719-0.555z"></path>
                    </svg>
                    <input id="search" type="text" autocomplete="off" placeholder="Search"/>
                </li>
            </ul>
            <div class="svg nav-toggle menu active">
                <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="28" height="28" viewBox="0 0 24 24"><path fill="#fff" d="M3 5h18q0.414 0 0.707 0.293t0.293 0.707-0.293 0.707-0.707 0.293h-18q-0.414 0-0.707-0.293t-0.293-0.707 0.293-0.707 0.707-0.293zM3 17h18q0.414 0 0.707 0.293t0.293 0.707-0.293 0.707-0.707 0.293h-18q-0.414 0-0.707-0.293t-0.293-0.707 0.293-0.707 0.707-0.293zM3 11h18q0.414 0 0.707 0.293t0.293 0.707-0.293 0.707-0.707 0.293h-18q-0.414 0-0.707-0.293t-0.293-0.707 0.293-0.707 0.707-0.293z"></path></svg>
            </div>
            <div class="svg nav-toggle exit">
                <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="28" height="28" viewBox="0 0 24 24"><path fill="#fff" d="M19 4q0.43 0 0.715 0.285t0.285 0.715q0 0.422-0.289 0.711l-6.297 6.289 6.297 6.289q0.289 0.289 0.289 0.711 0 0.43-0.285 0.715t-0.715 0.285q-0.422 0-0.711-0.289l-6.289-6.297-6.289 6.297q-0.289 0.289-0.711 0.289-0.43 0-0.715-0.285t-0.285-0.715q0-0.422 0.289-0.711l6.297-6.289-6.297-6.289q-0.289-0.289-0.289-0.711 0-0.43 0.285-0.715t0.715-0.285q0.422 0 0.711 0.289l6.289 6.297 6.289-6.297q0.289-0.289 0.711-0.289z"></path></svg>
            </div>
        </nav>
    </div>
    <div class="container-fluid"></div>
</header>