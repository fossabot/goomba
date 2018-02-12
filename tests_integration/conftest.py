import os
import time
from datetime import datetime
from subprocess import run

from click.testing import CliRunner
from elasticsearch import Elasticsearch
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

import requests
import pytest

dockerfile = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'docker-compose.yaml'
)


def pytest_configure(config):
    run(f'docker-compose -f {dockerfile} up -d'.split())


    # create client
    es = Elasticsearch('localhost', use_ssl=False, port=9200)

    print('Waiting for Elasticsearch ...')
    time.sleep(10)

    try:
        alive = es.ping()
        while not alive:
            time.sleep(1)
            alive = es.ping()
    except Exception:
        pass

    # index some bogus docs
    print('Indexing 100 bogus docs ...')
    for x in range(100):
        es.index(
            index='sample',
            doc_type='logs',
            body={'field': f'Hello World #{x}!'}
        )

    print('Waiting for Kibana ...')
    time.sleep(10)
    try:
        while not requests.head('http://localhost:5601/app/kibana', timeout=10.0).ok:
            time.sleep(1)
    except:
        pass

    # create initial pattern
    session = requests.Session()
    retry = Retry(total=2, status_forcelist=[409, 500, 503])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http', adapter)
    _payload = {
        'title': 'sample',
        'timeFieldName': '@timestamp',
        'notExpandable': True
    }
    _headers = {'kbn-xsrf': 'anything'}
    _params = {'op_type': 'create'}
    _url = 'http://localhost:5601/es_admin/.kibana/index-pattern/sample/_create'
    rv = session.post(
        _url,
        json=_payload,
        params=_params,
        headers=_headers
    )


def pytest_unconfigure(config):
    run(f'docker-compose -f {dockerfile} down'.split())
    run(f'docker-compose -f {dockerfile} rm -f -v'.split())
