import monkeypatches
import json
import sys
import os
import signal
import click
from click import BadParameter
import gevent
from gevent.event import Event
from devp2p.service import BaseService
from devp2p.peermanager import PeerManager
from devp2p.discovery import NodeDiscovery
from devp2p.app import BaseApp
from eth_service import ChainService
from console_service import Console
from ethereum.blocks import Block
import ethereum.slogging as slogging
import config as konfig
from db_service import DBService
from jsonrpc import JSONRPCServer
from pyethapp import __version__
import utils

from rno_service import RNOService

slogging.configure(config_string=':debug')
log = slogging.get_logger('app')


services = [DBService, NodeDiscovery, PeerManager, ChainService, JSONRPCServer, Console, RNOService]
services += utils.load_contrib_services()


class EthApp(BaseApp):
    client_version = 'pyethapp/v%s/%s/%s' % (__version__, sys.platform,
                                             'py%d.%d.%d' % sys.version_info[:3])
    default_config = dict(BaseApp.default_config)
    default_config['client_version'] = client_version


@click.group(help='Welcome to ethapp version:{}'.format(EthApp.client_version))
@click.option('alt_config', '--Config', '-C', type=click.File(), help='Alternative config file')
@click.option('config_values', '-c', multiple=True, type=str,
              help='Single configuration parameters (<param>=<value>)')
@click.option('data_dir', '--data-dir', '-d', multiple=False, type=str,
              help='data directory')
@click.option('log_config', '--log_config', '-l', multiple=False, type=str,
              help='log_config string: e.g. ":info,eth:debug')
@click.pass_context
def app(ctx, alt_config, config_values, data_dir, log_config):

    # configure logging
    log_config = log_config or ':info'
    slogging.configure(log_config)

    # data dir default or from cli option
    data_dir = data_dir or konfig.default_data_dir
    konfig.setup_data_dir(data_dir)  # if not available, sets up data_dir and required config
    log.info('using data in', path=data_dir)

    # prepare configuration
    # config files only contain required config (privkeys) and config different from the default
    if alt_config:  # specified config file
        config = konfig.load_config(alt_config)
    else:  # load config from default or set data_dir
        config = konfig.load_config(data_dir)

    config['data_dir'] = data_dir

    # add default config
    konfig.update_config_with_defaults(config, konfig.get_default_config([EthApp] + services))

    # override values with values from cmd line
    for config_value in config_values:
        try:
            konfig.set_config_param(config, config_value)
            # check if this is part of the default config
        except ValueError:
            raise BadParameter('Config parameter must be of the form "a.b.c=d" where "a.b.c" '
                               'specifies the parameter to set and d is a valid yaml value '
                               '(example: "-c jsonrpc.port=5000")')
    ctx.obj = {'config': config}


@app.command()
@click.option('--dev/--nodev', default=False, help='Exit at unhandled exceptions')
@click.pass_context
def run(ctx, dev):
    """Start the client"""
    # create app
    app = EthApp(ctx.obj['config'])

    if dev:
        gevent.get_hub().SYSTEM_ERROR = BaseException
        try:
            ctx.obj['config']['client_version'] += '/' + os.getlogin()
        except:
            log.warn("can't get and add login name to client_version")
            pass

    # register services
    for service in services:
        assert issubclass(service, BaseService)
        if service.name not in app.config['deactivated_services']:
            assert service.name not in app.services
            service.register_with_app(app)
            assert hasattr(app.services, service.name)

    # start app
    app.start()

    # wait for interupt
    evt = Event()
    gevent.signal(signal.SIGQUIT, evt.set)
    gevent.signal(signal.SIGTERM, evt.set)
    gevent.signal(signal.SIGINT, evt.set)
    evt.wait()

    # finally stop
    app.stop()


@app.command()
@click.pass_context
def config(ctx):
    """Show the config"""
    konfig.dump_config(ctx.obj['config'])


@app.command()
@click.argument('file', type=click.File(), required=True)
@click.pass_context
def blocktest(ctx, file):
    """Start after importing blocks from a file.

    It is recommended to turn the peermanager off when running block tests. If
    not the local test chain will be quickly replaced by the real one.
    """
    app = EthApp(ctx.obj['config'])
    app.config['db']['implementation'] = 'EphemDB'
    app.config['deactivated_services'] += 'peermanager'

    # register services
    for service in services:
        assert issubclass(service, BaseService)
        if service.name not in app.config['deactivated_services']:
            assert service.name not in app.services
            service.register_with_app(app)
            assert hasattr(app.services, service.name)

    if ChainService.name not in app.services:
        log.fatal('No chainmanager registered')
        ctx.abort()
    if DBService.name not in app.services:
        log.fatal('No db registered')
        ctx.abort()

    log.info('loading block file', path=file.name)
    try:
        data = json.load(file)
    except ValueError:
        log.fatal('Invalid JSON file')
    if len(data) != 1:
        log.fatal('Invalid file (not exactly one top level element)')
        ctx.abort()
    try:
        blocks = utils.load_block_tests(data.values()[0], app.services.chain.chain.db)
    except ValueError:
        log.fatal('Invalid blocks encountered')
        ctx.abort()

    # start app
    app.start()

    log.info('building blockchain')
    Block.is_genesis = lambda self: self.number == 0
    app.services.chain.chain._initialize_blockchain(genesis=blocks[0])
    for block in blocks[1:]:
        app.services.chain.chain.add_block(block)

    # wait for interupt
    evt = Event()
    gevent.signal(signal.SIGQUIT, evt.set)
    gevent.signal(signal.SIGTERM, evt.set)
    gevent.signal(signal.SIGINT, evt.set)
    evt.wait()

    # finally stop
    app.stop()


if __name__ == '__main__':
    #  python app.py 2>&1 | less +F
    app()
