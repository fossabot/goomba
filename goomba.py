import os
import copy
import logging
import logging.config
import sys
import time

import structlog
import click
import requests
import yaml
from urllib.parse import quote_plus
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

__version__ = '0.1'

# logging
logging.basicConfig(
    format='%(message)s', stream=sys.stdout, level=logging.INFO)

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level, structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper('iso'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# seriously, just shut up requests, I don't care!
logging.config.dictConfig({
    'version': 1,
    'loggers': {
        'requests.packages.urllib3': {
            'handlers': '',
            'level': 100
        }
    }
})

log = structlog.get_logger('goomba')


def _read_config(path):
    """Load dict from YAML file.

    Args:
        path (str): path to yaml file

    Returns:
        dict: Config dictionary

    """
    with open(path) as f:
        data = f.read()
    data = os.path.expandvars(data)
    data = yaml.safe_load(data)
    return data


def _build_config(data):
    """Build defaults and fill in cluster settings.

    Args:
        data (dict): raw config dict from :func:`_read_config`

    Returns:
        dict: Filled config dictionary

    """
    defaults = data['defaults']
    clusters = data['clusters']

    # set each cluster settings
    for cluster in clusters:

        # set each setting for each group if not present
        for group_key, group_val in defaults.items():
            if group_key in cluster:
                for key, val in group_val.items():
                    cluster[group_key].setdefault(key, val)
            else:
                cluster[group_key] = copy.deepcopy(group_val)

        # set default endpoint if nothing else is set for kibana
        cluster['kibana'].setdefault('url', cluster['es']['url'])

        # by default, exclude nothing!
        cluster.setdefault('exclude', [])
        cluster['exclude'] = set(cluster['exclude'])

    return data


def check_credentials(cluster):
    """Check if we can reach both Kibana & ES, set clients if we can.

    Args:
        cluster (dict): Cluster config dictionary

    Returns:
        bool: True if kibana & es can be reached, False otherwise

    """
    es_config = cluster['es']
    es_auth = (es_config['username'], es_config['password'])

    _app_path = '/app/kibana'
    kbn_config = cluster['kibana']
    kbn_auth = (kbn_config['username'], kbn_config['password'])
    kbn_config['auth'] = kbn_auth
    kbn_url = f'{kbn_config["protocol"]}://{kbn_config["url"]}:{kbn_config["port"]}'

    es = Elasticsearch(
        es_config['url'],
        use_ssl=True if es_config['protocol'] == 'https' else False,
        port=es_config['port'],
        verify_certs=True,
        http_auth=es_auth)

    try:
        if es.cluster.health():
            es_config['client'] = es
        rv = requests.head(
            f'{kbn_url}{_app_path}', auth=kbn_auth, timeout=10.0)
    except Exception as e:
        return False

    return rv.ok


def get_index_patterns(cluster):
    """Get index patterns for a given cluster.

    Args:
        cluster (dict): cluster config

    Returns:
        list: list of pattern titles

    """
    es_name = cluster['es']['url']
    es = cluster['es']['client']

    if not es.indices.exists('.kibana'):
        raise Exception('.kibana index on {es_name} is missing!')

    patterns_gen = scan(
        es,
        index='.kibana',
        doc_type='index-pattern',
        _source_include=['timeFieldName'])

    patterns = {}
    for doc in patterns_gen:
        if not doc['_id'].startswith(
                '.') and doc['_id'] not in cluster['exclude']:
            patterns[doc['_id']] = doc['_source'].get('timeFieldName')

    log.debug('fetched_patterns', patterns=patterns)

    return patterns


def refresh_index_patterns(cluster, patterns):
    """Refresh the index patterns for a given cluster.

    Args:
        cluster (dict): Cluster config dictionary
        patterns (list): list of titles/ids from :func:`get_index_patterns`

    """
    _refresh_path = '/es_admin/.kibana/index-pattern/'
    _headers = {'kbn-xsrf': 'anything'}
    kbn_config = cluster['kibana']
    kbn_auth = cluster['kibana']['auth']
    kbn_url = f'{kbn_config["protocol"]}://{kbn_config["url"]}:{kbn_config["port"]}'

    for pattern, timefield in patterns.items():
        quoted_pattern = quote_plus(pattern, safe='*')
        url = f'{kbn_url}{_refresh_path}{quoted_pattern}/'

        # if time series pattern, add timefield
        payload = {'title': pattern, 'notExpandable': True}
        if timefield:
            payload['timeFieldName'] = timefield

        rv = requests.post(url, json=payload, headers=_headers, auth=kbn_auth)
        log.debug('sent_refresh', pattern=pattern, payload=payload,
                url=url, response={**rv.__dict__})


@click.command()
@click.argument(
    'config',
    type=click.Path(exists=True, dir_okay=False),
    default='config.yaml')
@click.option(
    '-d', '--debug', default=False, is_flag=True, help='Debug logging')
def main(config, debug):
    """Refresh the Kibana mappings for all index-patterns on a given kibana
    Kibana instance and its related cluster."""

    # set debug level if applicable
    global log
    if debug:
        log.setLevel(logging.DEBUG)

    # build config
    config = _read_config(config)
    config = _build_config(config)

    # only check the good ones
    good = []
    for cluster in config['clusters']:
        log = log.bind(cluster=cluster['es']['url'])
        if check_credentials(cluster):
            good.append(cluster)
            log.debug('good_credentials')
        else:
            log.error('failed_credentials')

    # refresh the cluster(s) patterns
    for cluster in good:
        log = log.bind(cluster=cluster['es']['url'])
        start_time = time.time()
        patterns = get_index_patterns(cluster)
        time_series = [name for name, field in patterns.items() if field]
        normal_series = [name for name, field in patterns.items() if not field]
        refresh_index_patterns(cluster, patterns)
        log.info(
            'refreshed_patterns',
            timeseries_patterns=time_series,
            non_timeseries=normal_series,
            total_timeseries=len(time_series),
            total_non_timeseries=len(normal_series),
            total_series=len(time_series) + len(normal_series),
            duration=time.time() - start_time)

    log = log.unbind('cluster')
    log.debug('finished')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log.error('unexpected_error', exc_info=e)
    finally:
        sys.exit(0)
