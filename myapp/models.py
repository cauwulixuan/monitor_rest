#! /usr/bin/env python
# -*- coding: utf-8

from django.db import models
from django.contrib.auth.models import User
import json


class Instances(models.Model):
    '''
    创建一个 Instances 模型，与 Hosts 模型建立多对一的关系。
    只有 IP 和 PORT 两个字段，其中 IP 为 Hosts 模型的外键。
    '''
    instance = models.CharField(max_length=25)

    class Meta:
        ordering = ['instance']

    def save(self, *args, **kwargs):
        super(Instances, self).save(*args, **kwargs)

class Hosts(models.Model):
    '''
    建立 Hosts 模型，该模型包括 url, hosts,
    cpusage, memusage, diskusage 等字段，
    根据 url, hosts 等信息获取 Prometheus 的 metrics 数据。
    '''
    href = models.URLField()
    hosts = models.ForeignKey(Instances, related_name='hosts', on_delete=models.CASCADE)

    cpusage = models.TextField()
    memusage = models.TextField()
    diskusage = models.TextField()
    load = models.TextField()

    class Meta:
        ordering = ['hosts']

    def save(self, *args, **kwargs):
        super(Hosts, self).save(*args, **kwargs)


