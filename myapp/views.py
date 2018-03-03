#!/usr/bin/python
#-*- coding:utf-8 -*-

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .models import Hosts, Instances
from .serializers import HostsSerializer, InstancesSerializer
from .parse import ParseUtil, ScrapeMetrics
from configparser import ConfigParser
import json
from rest_framework.decorators import api_view
from . import params

url = params.prometheus_url
print('url=', url)
h = ScrapeMetrics(url)

import sys
sys.path.append('..')
import metrics.monitor

@api_view(['GET'])
def hosts_list(request):
    """
    List all hosts.
    """
    if request.method == 'GET':
        return JsonResponse(h.hosts_list_metrics(), safe=False)
    

@api_view(['GET'])
def host_detail(request, pk):
    """
    Retrieve a host by pk = instance.
    """
    if request.method == 'GET':
        try:
            h.host_detail_metrics(pk)
        except:
            return JsonResponse('KeyError! not found key {0}'.format(pk),status=404, safe=False)
        else:
            return JsonResponse(h.host_detail_metrics(pk), safe=False)

@api_view(['GET'])
def module_list(request):
    """
    List all module metrics.
    """
    if request.method == 'GET':
        return JsonResponse(metrics.monitor.monitor_metrics(), safe=False)

@api_view(['GET'])
def test(request):
    """
    List all module metrics.
    """
    import test_metrics
    if request.method == 'GET':
        print test_metrics
        return JsonResponse(test_metrics.test, safe=False)        
