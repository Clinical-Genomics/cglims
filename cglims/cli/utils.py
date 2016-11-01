# -*- coding: utf-8 -*-
import datetime
import json
import re
from cStringIO import StringIO


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


def fix_dump(dump, indentSize=2):
    stream = StringIO(dump)
    out = StringIO()
    pattern = re.compile('(\s*)([^:]*)(:*)')
    last = None

    prefix = 0
    for line in stream:
        indent, key, colon = pattern.match(line).groups()
        if indent == "" and key[0] != '-':
            prefix = 0
        if last:
            if len(last[0]) == len(indent) and last[2] == ':':
                if all([not last[1].startswith('-'),
                        line.strip().startswith('-')]):
                    prefix += indentSize
        out.write(" " * prefix + line)
        last = indent, key, colon
    return out.getvalue()
