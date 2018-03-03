#!/usr/bin/env python2
#-*- coding: utf-8 -*-

# define consul cluster ip and port, both set to be string.
# consul_ip can be set to several values, seperated by ",".
consul_ip = "172.16.1.10, 172.16.1.14, 172.16.1.41"
consul_port = "8500"

rest_api_url = "http://10.10.6.214:19030"
prometheus_url = "http://10.10.6.214:9500"
