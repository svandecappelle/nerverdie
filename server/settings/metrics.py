# -*- coding: utf-8 -*-

AVAILABLE_METRICS = [
    'cpu',
    'mem',
    'sensors',
    'disk',
    'uptime',
    'system_info'
]

SINGLE_METRICS = {
    'system': [
        'status',
        'uptime'
    ],
    'memory': [
        'available',
        'total'
    ],
    'disk': [
        'available',
        'used'
    ],
    'proc': [
        'cores'
    ]
}
