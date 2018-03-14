#!/usr/bin/python
#-*- coding:utf-8 -*-

from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^api/v1/monitor/$', views.module_list),
    url(r'^api/v1/hosts/$', views.hosts_list),
    url(r'^api/v1/hosts/(?P<pk>((?:(?:25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?\d)))\.){3}(?:25[0-5]|2[0-4]\d|((1\d{2})|([1-9]?[1-9])))(\:\d{1,6})))/$', views.host_detail),
]
