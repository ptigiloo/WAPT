#-------------------------------------------------------------------------------
# Name:        create_setup.py
# Purpose:
#
# Author:      Administrateur
#
# Created:     16/09/2013
# Copyright:   (c) Tranquil IT Systems 2013-2014
# Licence:     GPL v3
#-------------------------------------------------------------------------------

import os
import sys

import subprocess
import ConfigParser
import paramiko
import shutil
import getpass
import glob
import win32api

"""
depends on paramiko

pour le fichier autobuild.ini, la syntaxe est la suivante:
[global]
svn_username=xxxxxx
svn_password=xxxxxxx
checkout_dir=c:\\xxxxxxx
svnroot=https://srvsvn/wapt/trunk
ssh_username = root
ssh_private_key = c:\private\srvwapt_priv.key
ssh_hostname = srvwapt
ssh_log_file = c:\tranquilit\paramiko.log
ksigntool_path=C:\Program Files\kSign\kSignCMD.exe
private_key=c:\private\certificat.p12
key_password=xxxxxxxxx
ksign=C:\Program Files\kSign\kSignCMD.exe /f C:\private\certificat.p12 /p xxxxxxxx $p

Installation de pycrypto depuis
http://www.voidspace.org.uk/python/modules.shtml#pycrypto

Installation paramiko avec easy_install
easy_install paramiko

"""


def programfiles32():
    """Return 32bits applications folder."""
    if 'PROGRAMW6432' in os.environ and 'PROGRAMFILES(X86)' in os.environ:
        return os.environ['PROGRAMFILES(X86)']
    else:
        return os.environ['PROGRAMFILES']


def ssl_server_trust_prompt( trust_dict ):
    return True, trust_dict['failures'], True

def get_required_param(param_name,section='global'):
    global config
    if config.has_option(section, param_name):
        return config.get(section, param_name)
    else:
        raise Exception ("missing parameter %s in section %s config file",(param_name,section))


def update_waptupgrade(checkout_dir):
    print('Building a new waptupgrade package')
    sys.path.append('c:/wapt')
    from common import Wapt
    wapt = Wapt()
    wapt.build_upload(os.path.join(checkout_dir,'waptupgrade'))


def sign_all_exe(ksigntool_path,private_key,key_password,checkout_dir):
    for file_to_sign in glob.glob(checkout_dir + "\\*.exe"):
        print file_to_sign
        cmd = """ "%(ksigntool_path)s" \
        /d "Binary part of Wapt-get software management suite" \
        /du http://dev.tranquil.it \
        /f %(private_key)s  \
        /p %(key_password)s \
        "%(file_to_sign)s" """  % {
                        'ksigntool_path':ksigntool_path,
                        'private_key':private_key,
                        'key_password':key_password,
                        'file_to_sign':file_to_sign,
                        }

        print cmd
        print subprocess.check_output(cmd, shell=True)
######################


config_file = "c:\\private\\autobuild.ini"
config = ConfigParser.RawConfigParser()



if os.path.exists(config_file):
    config.read(config_file)
else:
    raise Exception("FATAL. Couldn't open config file : " + config_file)

if config.has_section('global'):
    svn_username = get_required_param('svn_username')
    svn_password = get_required_param('svn_password')
    checkout_dir = get_required_param('checkout_dir')
    svnroot = get_required_param('svnroot')
    ssh_username = get_required_param('ssh_username')
    ssh_private_key = get_required_param('ssh_private_key')
    ssh_hostname = get_required_param('ssh_hostname')
    ssh_log_file = get_required_param('ssh_log_file')

    if config.has_option('global','ksigntool_path'):
        ksigntool_path =get_required_param('ksigntool_path')
    else:
        ksigntool_path = os.path.join(programfiles32(),'ksign','kSignCMD.exe')


    private_key = get_required_param('private_key')
    private_key_p12 = get_required_param('private_key_p12')
else:
    raise Exception ('missing [global] section')


key_password = getpass.getpass('Signing key password :')
print '\n'

if os.path.exists(ksigntool_path)==False:
    print "FATAL: ksigntool_path %s does not exists" % ksigntool_path
    sys.exit(1)
if os.path.exists(private_key)==False:
    print "FATAL: private_key file %s does not exists" % private_key
    sys.exit(1)

# if there is space in the name, we have to protect it with quote

if ' ' in ksigntool_path:
    ksigntool_path_protected = win32api.GetShortPathName(ksigntool_path)
else:
    ksigntool_path_protected=ksigntool_path

if ' ' in private_key:
    private_key_protected= win32api.GetShortPathName(private_key_p12)
else:
    private_key_protected = private_key_p12

#ksigntool_path_protected = "C:\\progra~2\\kSign\\kSignCMD.exe"
ksign = """%(ksigntool_path)s /f %(private_key)s /p %(key_password)s $p""" % {
            'ksigntool_path':ksigntool_path_protected,
            'private_key':private_key_protected,
            'key_password':key_password}

print ksign

rev = open(os.path.join(checkout_dir,'version'),'r').read().strip()

###CHECKOUT
print "checkout du projet"
if not os.path.isdir(os.path.dirname(checkout_dir)):
    os.mkdir(os.path.dirname(checkout_dir))
    print subprocess.check_output('git clone git://srvdev/wapt.git "%s"' % checkout_dir)
else:
    os.chdir(checkout_dir)
    print subprocess.check_output('git checkout -f --')

rev = open(os.path.join(checkout_dir,'version'),'r').read().strip()

### .EXE Signature
sign_all_exe(ksigntool_path,private_key_p12,key_password,checkout_dir)

### update WAPT upgrade package
update_waptupgrade(checkout_dir)

issc_binary = os.path.join(programfiles32(),'Inno Setup 5','ISCC.exe')

for buildtype in ('waptserver','waptsetup','waptstarter'):
    print "building %s_%s.exe" % (buildtype,rev)

    issfile = os.path.join(checkout_dir,'waptsetup','%s.iss'%buildtype )
    print "running waptsetup for iss file : %s " % issfile
    cmd = '"%(issc_binary)s" /s"kSign=%(ksign)s" /f%(buildtype)s_rev%(rev)s %(issfile)s' % {
                    'issc_binary':issc_binary,
                    'ksign':ksign,
                    'buildtype':buildtype,
                    'rev':rev,
                    'issfile':issfile
                    }
    print "ligne de commande : %s " % cmd
    print subprocess.check_output(cmd)
                            #,'' % (buildtype,rev),"%s"%issfile])

    localfile = os.path.join(os.path.dirname(issfile),'%s_rev%s.exe' % (buildtype,rev) )
    remotefile = os.path.join('/var/www/wapt/nightly/','%s_rev%s.exe' % (buildtype,rev))

    print "uploading %s to remote server" % localfile
    print remotefile
    paramiko.util.log_to_file(ssh_log_file)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(
                paramiko.AutoAddPolicy())
    my_key = paramiko.DSSKey.from_private_key_file(ssh_private_key)
    ssh.connect(ssh_hostname,port=22,username=ssh_username,pkey=my_key,timeout=10)
    sftp = ssh.open_sftp()
    sftp.put(remotepath=remotefile, localpath=localfile)
    sftp.close()
    ssh.close()
