import hashlib
import json
import os

from collections import Counter

from datetime import datetime, timedelta
from pprint import pprint
from urllib import urlencode

import requests

bugzilla_rest = 'https://bugzilla.mozilla.org/rest/bug?'


def intermittents(person, **kw):
    kw = kw.copy()
    kw.update({
        'emailtype1': 'exact',
        'emailreporter1': '1',
        'email1': person,
        'product': 'Toolkit',
        'component': 'Add-ons Manager'
    })
    return kw


def rest_query(query, cache=True):
    query = bugzilla_rest + urlencode(query)

    query_hash = hashlib.md5()
    query_hash.update(query)
    cache_key = 'bugzilla:' + query_hash.hexdigest()
    filename = os.path.join('cache', cache_key + '.json')

    if cache and os.path.exists(filename):
        return json.load(open(filename, 'r'))

    log.info('Bugzilla: {}'.format(query))
    print query
    result = requests.get(query).json()
    if cache:
        json.dump(result, open(filename, 'w'))

    return result


def output_keys(key):
    for k in sorted(stats.keys()):
        if k.startswith(key):
            print '{}: {}, {:.3f}%'.format(
                k[len(key):], 
                stats[k], 
                (stats[k] / float(stats['total'])) * 100
            )

if __name__=='__main__':
    query = intermittents('intermittent-bug-filer@mozilla.bugs')
    result = rest_query(query, cache=True)
    
    taken = []
    stats = Counter()
    stats['total'] = len(result['bugs'])
    for k, bug in enumerate(result['bugs']):
        status = ('{} {}'.format(bug['status'], bug['resolution'])).strip()
        stats.update({'resolution-' + status: 1})
        if status.startswith('RESOLVED'):
            stats.update({'resolved': 1})
        if bug['cf_last_resolved']:
            fmt = '%Y-%m-%dT%H:%M:%SZ'
            diff = (
                datetime.strptime(bug['cf_last_resolved'], fmt) - 
                datetime.strptime(bug['creation_time'], fmt)
            )
            taken.append(diff)
        stats.update({'priority-' + bug['priority']: 1})

    avg = timedelta(seconds=sum([i.total_seconds() for i in taken]) / len(taken))
    print 'Number of bugs: {}'.format(stats['total'])
    print 'Number resolved: {}, {:.3f}%'.format(
        stats['resolved'], (stats['resolved'] / float(stats['total'])) * 100
    )
    print 'Average time to resolution (days, h:m:s): {}'.format(avg)
    print 
    output_keys('resolution-')
    print
    output_keys('priority-')
    