#!/usr/bin/env python

import os
import time

from fabric.api import task, env, run, sudo, execute
from fabric.contrib import files
from fabric.utils import error

env.use_ssh_config = True
env.forward_agent = True

datetime_format = '%Y%m%d%H%M%S'
env.hosts    = ['support-tools-1.vpc3.10gen.cc']

app          = 'support-tools'
repo         = 'git@github.com:10gen/support-services.git'
env.environment  = 'prod'
group        = 'support-tools'

piddir = '/var/run/10gen'
logdir = '/var/log/10gen'

@task
def vagrant():
    # fab vagrant deploy
    env.environment  = 'dev'
    set_variables(app)

    env.user = 'vagrant'
    env.hosts = ['127.0.0.1:2222']
    env.key_filename = '~/.vagrant.d/insecure_private_key'

    execute(vagrant_group)

def vagrant_group():
    sudo('usermod -a -G {0} vagrant'.format(env.deploy_group))

@task
def staging():
    env.environment = 'staging'
    set_variables(app)

    env.hosts = ['support-dashboard-staging-1.vpc3.10gen.cc']

def set_variables(deploy_app):
    env.deploy_name  = app + '-' + env.environment
    env.deploy_group = group + '-' + env.environment
    env.base_dir     = os.path.join('/opt/10gen', env.deploy_name, deploy_app)
    env.current_link = os.path.join(env.base_dir, 'current')
    env.scripts_link = os.path.join(env.base_dir, 'scripts')
    env.releases_dir = os.path.join(env.base_dir, 'releases')
    env.init = '/etc/init.d'

@task
def deploy(app=None, branch='master'):

    if not app:
        error("App to deploy must be specified. e.g.:\n\n fab deploy:euphonia\n fab staging deploy:karakuri,branch=staging\n fab deploy:karakurid,test_branch\n")

    set_variables(app)

    projects = {
        'karakuri': {
            'requirements': os.path.join(env.current_link, 'karakuri', 'requirements.txt'),
            'config':       os.path.join(env.current_link, 'karakuri', 'karakuri.cfg'),
            'init':         os.path.join(env.init, 'karakuri')
        },
        'karakurid': {
            'config':       os.path.join(env.current_link, 'karakuri', 'karakurid.cfg'),
            'init':         os.path.join(env.init, 'karakurid')
        },
        'euphonia': {
            'requirements': os.path.join(env.current_link, 'proactivedb', 'requirements.txt'),
            'config':       os.path.join(env.current_link, 'proactivedb', 'euphonia.cfg'),
            'init':         os.path.join(env.init, 'euphonia')
        },
        'teledangos': {
            'requirements': os.path.join(env.current_link, 'teledangos', 'requirements.txt'),
            'init':         os.path.join(env.init, 'teledangos')
        }
    }

    try:
        project = projects[app]
    except:
        error("The specified project has not been defined: {}".format(app))

    now = time.strftime(datetime_format)
    deploy_dir       = os.path.join(env.releases_dir, now)

    scl = 'scl enable python27'
    virtualenv_dir = os.path.join(env.base_dir, 'virtualenv')
    virtualenv_pip = os.path.join(virtualenv_dir, 'bin/pip')

    run('git clone -b {branch} {repo} {dest}'.format(branch=branch, repo=repo, dest=deploy_dir))
    run('chmod 2775 {0}'.format(deploy_dir))

    # update the current deployment symlink
    run('ln -sfn {0} {1}'.format(deploy_dir, env.current_link))

    # install requirements
    run("{0} '{1} install -r {2}'".format(
        scl,
        virtualenv_pip,
        os.path.join(env.current_link, 'requirements.txt')
        ))


    # config file symlink
    if 'config' in project:
        path, filename = os.path.split(project['config'])
        run('ln -sfn {0} {1}'.format(os.path.join(env.base_dir, filename), path))

    # restart service
    if 'init' in project:
        run('sudo {0} restart'.format(project['init']))

