from rest_framework import serializers
from .models import Hosts, Instances


class HostsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hosts
        fields = '__all__'

class InstancesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instances
        fileds = '__all__'