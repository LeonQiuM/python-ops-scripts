#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Author : Leon
# python version 3
# Date 2017/8/17
"'jstat -gccapacity {pid} | grep -v NG'.format(pid=pid)"

import paramiko
import threading
import time
import requests
import json
import gevent
from gevent import monkey
monkey.patch_all()

#ssh
private_key = paramiko.RSAKey.from_private_key_file('~/.ssh/id_rsa_root')

#server list
HostList = [
    "host1",
    "host2",
    "192.168.1.1"
]


def ssh_client(hostname,cmd):
    '''
    ssh connect
    :param hostname:
    :param cmd:
    :return:
    '''
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname=hostname, port=22, username="root", pkey=private_key)
    result = None
    try:
        stdin,stdout,stderr = ssh.exec_command(cmd)
        result = stdout.read()
    except Exception as e:
        print(e)

    return result


def get_pid(hostname):
    '''
    get process pid
    :param hostname:
    :return:
    '''
    result = {}
    Cmd8080Get = "ps -ef | grep 8080_tomcat_server |grep -v grep  |awk '{print $2}'"
    Cmd8081Get = "ps -ef | grep 8081_tomcat_server |grep -v grep  |awk '{print $2}'"
    pid_8080 = ssh_client(hostname,Cmd8080Get)
    pid_8081 = ssh_client(hostname,Cmd8081Get)
    result["8080"] = pid_8080.strip()
    result["8081"] = pid_8081.strip()
    return result


def jvm_info(hostname):
    '''
    get jvm gc information
    :param hostname:
    :return:
    '''
    jvm_result = {}
    pid_info = get_pid(hostname)
    for item in pid_info:
        jstat_cmd = 'jstat -gccapacity %s '%pid_info[item]
        jstat_cmd2 = 'jstat -gc %s '%pid_info[item]
        info_list = ssh_client(hostname,jstat_cmd).split()[18:]
        info_list_2 = ssh_client(hostname,jstat_cmd2).split()[17:]
        info_list.append(info_list_2[13])
        info_list.append(info_list_2[15])
        info_list.append(info_list_2[16])
        jvm_result[item] = info_list
    return jvm_result


def push(endpoint,metric,value,port):
    '''
    push to open-falcon
    :param endpoint:
    :param metric:
    :param value:
    :param port:
    :return:
    '''
    payload = [
        {
            "endpoint": endpoint,
            "metric": metric,
            "timestamp": int(time.time()),
            "step": 60,
            "value": value,
            "counterType": "GAUGE",
            "tags": "port={port}".format(port=port),
        }
    ]
    requests.post("http://127.0.0.1:1988/v1/push", data=json.dumps(payload))


def run(hostname):
    data = jvm_info(hostname) #dic
    for item in data:
        ans_data = {}
        ans_data["NGCMN"] = float(data[item][0])/1024
        ans_data["NGCMX"] = float(data[item][1])/1024
        ans_data["NGC"] = float(data[item][2])/1024
        ans_data["S0C"] = float(data[item][3])/1024
        ans_data["S1C"] = float(data[item][4])/1024
        ans_data["EC"] = float(data[item][5])/1024
        ans_data["OGCMN"] = float(data[item][6])/1024
        ans_data["OGCMX"] = float(data[item][7])/1024
        ans_data["OGC"] = float(data[item][8])/1024
        ans_data["OC"] = float(data[item][9])/1024
        ans_data["MCMN"] = float(data[item][10])/1024
        ans_data["MCMX"] = float(data[item][11])/1024
        ans_data["MC"] = float(data[item][12])/1024
        ans_data["CCSMN"] = float(data[item][13])/1024
        ans_data["CCSMX"] = float(data[item][14])/1024
        ans_data["CCSC"] = float(data[item][15])/1024
        ans_data["YGC"] = data[item][16]
        ans_data["FGC"] = data[item][17]
        ans_data["YGCT"] = data[item][18]
        ans_data["FGCT"] = data[item][19]
        ans_data["GCT"] = data[item][20]
        for i in ans_data:
            push(hostname,i,float(ans_data[i]),item)


if __name__ == '__main__':
    for host in HostList:
        gevent.joinall([
            gevent.spawn(run,host),
        ])



