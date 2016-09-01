# -*- coding: utf-8 -*-
import datetime
import json

from cglims.api import ClinicalLims


def connect_api(config):
    """Connect and return API reference."""
    api = ClinicalLims(config['host'], config['username'], config['password'])
    return api


def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime.datetime):
        serial = obj.isoformat()
        return serial
    raise TypeError('Type not serializable')


def jsonify(data, pretty=False):
    """Serialize Model to JSON."""
    kwargs = dict(indent=4, sort_keys=True) if pretty else dict()
    return json.dumps(data, default=json_serial, **kwargs)
