import json
import logging
import os

from click.testing import CliRunner
from elasticsearch import Elasticsearch

import pytest
from goomba import main

goomba_config = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'sample.yaml'
)


def goomba_run(*args):
    runner = CliRunner()
    return runner.invoke(main, args)


def test_goomba():

    es = Elasticsearch('localhost', port=9200, use_ssl=False)
    before = es.get(index='.kibana', doc_type='index-pattern', id='sample')
    es.index(
        index='sample',
        doc_type='logs',
        body={'other': f'I am new here'}
    )

    initial_run = goomba_run('--debug', goomba_config)
    assert initial_run.exit_code == 0

    after = es.get(index='.kibana', doc_type='index-pattern', id='sample')

    assert before['_source'] != after['_source']
    assert before['_version'] != after['_version']
