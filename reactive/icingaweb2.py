import pwd
import os
import time
import subprocess
from subprocess import check_output, check_call
from charmhelpers.core.hookenv import status_set, relation_get, config
from charmhelpers.core.templating import render
from charms.reactive import when, when_not
from charms.reactive import set_state, remove_state
from charmhelpers import fetch

@when('apache.available', 'database.available')
def setup_icinga2(mysql):
    fetch.add_source('ppa:formorer/icinga')
    fetch.apt_update(fatal=True)
    packages = ['icinga2', 'icinga2-ido-mysql']
    fetch.apt_install(fetch.filter_installed_packages(packages))
    check_call(['a2enmod', 'rewrite'])
    check_call(['icinga2', 'feature', 'enable', 'ido-mysql'])
    render(source='features-available/ido-mysql.conf',
           target='/etc/icinga2/features-available/ido-mysql.conf',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    render(source='resources.ini',
           target='/etc/icingaweb2/resources.ini',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    render(source='config.ini',
           target='/etc/icingaweb2/config.ini',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    render(source='authentication.ini',
           target='/etc/icingaweb2/authentication.ini',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    render(source='roles.ini',
           target='/etc/icingaweb2/roles.ini',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    render(source='modules/monitoring/config.ini',
           target='/etc/icingaweb2/modules/monitoring/config.ini',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    render(source='modules/monitoring/backends.ini',
           target='/etc/icingaweb2/modules/monitoring/backends.ini',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    render(source='modules/monitoring/commandtransports.ini',
           target='/etc/icingaweb2/modules/monitoring/commandtransports.ini',
           owner='www-data',
           perms=0o775,
           context={
               'db': mysql,
           })
    check_call(['/etc/init.d/icinga2', 'restart'])
    set_state('apache.start')
    status_set('maintenance', 'Starting Apache')

@when('database.available')
def create_tables(mysql):
    charm_config = config()
    admin_password = charm_config['admin_password']
    admin_hash = generate_admin_hash(admin_password)
    host = relation_get('host')
    user = relation_get('user')
    password = relation_get('password')
    database = relation_get('database')
    proc = subprocess.Popen(["mysql", "--user=%s" % user, "--host=%s" % host, "--password=%s" % password, database], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = proc.communicate("SHOW TABLES LIKE 'icinga%%'")
    if out == '':
        sql=open("files/icingaweb2.sql").read()
        proc = subprocess.Popen(["mysql", "--user=%s" % user, "--host=%s" % host, "--password=%s" % password, database], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = proc.communicate(sql)
        sql="INSERT INTO icingaweb_user (name, active, password_hash) VALUES ('icingaadmin', 1, '%s')" % admin_hash
        proc = subprocess.Popen(["mysql", "--user=%s" % user, "--host=%s" % host, "--password=%s" % password, database], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = proc.communicate(sql)
        sql=open("files/icinga2.sql").read()
        proc = subprocess.Popen(["mysql", "--user=%s" % user, "--host=%s" % host, "--password=%s" % password, database], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        out, err = proc.communicate(sql)


def generate_admin_hash(password):
    hash = check_output(["openssl", "passwd", "-1", password]).rstrip(os.linesep)
    return hash

@when('apache.available')
@when_not('database.connected')
def missing_mysql():
    remove_state('apache.start')
    status_set('blocked', 'Please add relation to MySQL')

@when('database.connected')
@when_not('database.available')
def waiting_mysql(mysql):
    remove_state('apache.start')
    status_set('waiting', 'Waiting for MySQL')

@when('apache.started')
def started():
    status_set('active', 'Ready')
