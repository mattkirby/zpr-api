#!/usr/bin/env python2
"""
Serialize data from task spooler, gather system data and ship to elasticsearch

This library will help gather data from task spooler and help
send it to elasticsearch, or return json.
"""

import re
import os
import datetime
import sys

from subprocess import check_output, call
from elasticsearch import Elasticsearch
from socket import getfqdn


class Tsp:
    """
    Gather data from task spooler and send it away
    """

    def __init__(self):
        self.output = []
        self.results = []
        self.toremove = []

    def get_output(self, search=None):
        """
        Get output from taskspooler about finished jobs
        """
        tspout = check_output('tsp').split('\n')
        for i in tspout[1:-1]:
            if i.split()[1] == 'finished':
                if search:
                    if re.compile(search).findall(i):
                        self.output.append(i.split())
                else:
                    self.output.append(i.split())

    def get_results(self):
        """
        Gather exit code and job file for a tsp job
        """
        for i in self.output:
            results = {}
            toremove = {}
            index = self.output[self.output.index(i)]
            tspfile = index[2]
            toremove['tspid'] = index[0]
            toremove['tspfile'] = tspfile
            results['title'] = index[-1].split('/')[-1]
            results['worker'] = getfqdn()
            results['exit_code'] = index[3]
            results['time'] = self.get_timestamp(tspfile)
            results['command'] = index[5:]
            results['primary_storage'] = self.check_nfs_source(results['title'])
            results['host_url'] = self.get_target_fqdn(index)
            tspfile = toremove['tspfile']
            if os.path.isfile(tspfile):
                results['changes'] = self.read_file(tspfile)
                err_file = str('{}.e'.format(tspfile))
                if os.path.isfile(err_file):
                    results['errors'] = self.read_file(err_file)
            snapdir = str('/srv/backup/{}/.zfs/snapshot'.format(results['title']))
            if os.path.exists(snapdir):
                results['snapshots'] = os.listdir(snapdir)
            self.results.append(results)
            self.toremove.append(toremove)
        self.check_if_changes()

    def check_if_changes(self, out='changes', err='errors'):
        """
        Checks for content in changes and errors. Populates has_changes / has_errors
        """
        for i in self.results:
            if not i.get(out) == None: # Check if there are any changes
                if i[out] == []:
                    i['has_{}'.format(out)] = False
                    del i[out]
                else:
                    i['has_{}'.format(out)] = True
            if not i.get(err) == None:
                if i[err] == []:
                    i['has_{}'.format(err)] = False
                    del i[err]
                else:
                    i['has_{}'.format(err)] = True
            else:
                if i['exit_code'] == '0':
                    i['has_{}'.format(err)] = False
                else:
                    i['has_{}'.format(err)] = True

    @staticmethod
    def get_timestamp(filename):
        """
        Get a formated timestamp of the last modified time of a file
        """
        file_mtime = os.path.getmtime(filename)
        time_format = '%Y-%m-%dT%H:%M:%S%z'
        mtime = datetime.datetime.fromtimestamp(file_mtime).strftime(time_format)
        return mtime

    @staticmethod
    def read_file(filename):
        """
        Get the output of a file and return a list
        """
        file_out = []
        for i in open(filename):
            file_out.append(i.strip())
        return file_out

    @staticmethod
    def check_nfs_source(title):
        """
        Checks /etc/fstab for source of a nfs mount
        """
        for i in open('/etc/fstab'):
            if re.compile(title).findall(i):
                if re.compile('^{}$'.format(title)).findall(i.split()[1].split('/')[-1]):
                    return i.split(':')[0]

    @staticmethod
    def get_target_fqdn(source, user='zpr_proxy'):
        """
        Get the fqdn of the job target
        """
        for i in source:
            if re.compile('^{}@'.format(user)).findall(i):
                return i.split('@')[-1].split(':')[0]

    @staticmethod
    def remove_task(taskid):
        """
        Remove a job from the taskspooler list
        """
        check_output(['tsp', '-r', taskid])

    @staticmethod
    def send_to_elasticsearch(
            content,
            index='zpr',
            doc='zpr_job',
            url='elasticsearch.ops.puppetlabs.net',
            esid=None
        ):
        """
        Send results to elasticsearch in the specified index
        """
        es = Elasticsearch([{'host': url, 'port': 9200}])
        if es.ping():
            es.index(index, doc, content, id=esid)
        else:
            sys.exit(1)

    @staticmethod
    def list_files(startpath):
        """
        List a file tree in json
        """
        tree = []
        for root, dirs, files in os.walk(startpath):
            root_list = {'directory': '{}/'.format(os.path.basename(root))}
            file_list = []
            for filename in files:
                file_list.append(filename)
            root_list['files'] = file_list
            tree.append(root_list)
        return tree
