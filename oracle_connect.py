#!/usr/bin/python
#
# Copyright (C) 2018 Terence Ho <terenho@hotmail.com>
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with it.  If not, see <http://www.gnu.org/licenses/>.
#

import csv
import os
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/oracle/12.2/client64/lib'
import pprint
import re
import subprocess
from subprocess import Popen, PIPE
import sys

host = "" # whether command is --host or --list

if (len(sys.argv) == 2 and sys.argv[1] == "--list"):
  host = ""
elif (len(sys.argv) == 3 and sys.argv[1] == '--host'):
  host = sys.argv[2]
else:
  print ("\033[91musage: ansible-inventory.py (--list | --host <host>)\033[0m")
  sys.exit(1)

hostgroups = dict();
hosts = set();
hostvars = dict();

# Connect to Oracle DB to retrieve host info
pipe = Popen(['/usr/bin/sqlplus64', '-S', 'system/password@10.1.5.131/XE'], stdout=PIPE, stdin=PIPE)

output = pipe.communicate(input="""
SET FEEDBACK OFF;
SET HEADING OFF;
SET SERVEROUTPUT ON;

EXECUTE DBMS_OUTPUT.PUT_LINE('HOSTNAME,OS_TYPE');
SELECT HOSTNAME || ','|| OS_TYPE FROM SYSTEM;
""")[0]

output = output.decode()
output = re.sub('^\s*\n', '', output, flags=re.MULTILINE)
output = iter(output.splitlines())
reader = csv.DictReader(output)
for row in reader:
  hosts.add(row['HOSTNAME'].lower())
  hostvars[row['HOSTNAME'].lower()]={'os_type': row['OS_TYPE'].lower()}


# Connect to Oracle DB to retrieve database information
pipe = Popen(['/usr/bin/sqlplus64', '-S', 'system/password@10.1.5.131/XE'], stdout=PIPE, stdin=PIPE)

output = pipe.communicate(input="""
SET FEEDBACK OFF;
SET HEADING OFF;
SET SERVEROUTPUT ON;

EXECUTE DBMS_OUTPUT.PUT_LINE('HOSTNAME,PRODUCTNAME');
SELECT SYSTEM.HOSTNAME || ','|| DATABASE.PRODUCTNAME
  FROM SYSTEM
  INNER JOIN DATABASE ON SYSTEM.HOSTNAME = DATABASE.HOSTNAME;
""")[0]

output = output.decode()
output = re.sub('^\s*\n', '', output, flags=re.MULTILINE)
output = iter(output.splitlines())
reader = csv.DictReader(output)
for row in reader:
  hostvars[row['HOSTNAME'].lower()][row['PRODUCTNAME'].lower()]=row['PRODUCTNAME'].lower()

inventory_path = os.path.dirname(os.path.realpath(__file__))
# add custom lists into hostgroups
groupfiles = [f for f in os.listdir(inventory_path + '/lists') if os.path.isfile(os.path.join(inventory_path + '/lists', f))]

for groupfile in groupfiles:
  groupname = os.path.splitext(groupfile)[0].lower()
  if (groupname in hostgroups or groupname == 'all'):
    print("\033[91mhostgroup: \033[95m" + groupname + "\033[91m is already defined\033[0m")
    sys.exit(1)
  hostgroups[groupname] = {'hosts' : []}
  f = open(inventory_path + '/lists/' + groupfile, 'r')
  for line in f:
    grouphost = line.strip(' \n').lower()
    if (grouphost not in hosts):
      print("\033[91mgrouphost: \033[95m" + grouphost + "\033[91m is not in the database\033[0m")
      sys.exit(1)
    hostgroups[groupname]['hosts'].append(grouphost)

pp = pprint.PrettyPrinter(indent=2)
if (host == ""):
  listalldoc = {'_meta': {"hostvars": hostvars}, "all": {"hosts": list(hosts)}}
  listalldoc.update(hostgroups)
  pp.pprint(listalldoc)
else:
  if (host in hosts):
    pp.pprint(hostvars[host])
  else:
    print("\033[91mhost: \033[95m" + host + "\033[91m is not in the database\033[0m")
    sys.exit(1)
