# Copyright 2016 IBM Corp. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import json
import logging
import traceback

from flask import g, request
from flask_restful import Resource, reqparse

from app import docker_client as docker
from app import redis_client, app


# def paging(ndx, page, limit):
#    return page * limit <= ndx < (page + 1) * limit


def extract_source_ip():
    # Need to ge the source IP address of the request.
    # We can then log this information in our routing table on connect
    # And remove it on disconnect. ASSUMES NGINX
    return request.environ.get('HTTP_X_REAL_IP', request.remote_addr)


class GameServerList(Resource):

    def __parse_get_args(self):
        gs_parser = reqparse.RequestParser()
        gs_parser.add_argument('limit', type=int)
        return gs_parser.parse_args()

    def _minimal(d):
        ip = d['NetworkSettings']['IPAddress']
        port = app.config["GAME_PORT"]
        n_d = {k: v for k, v in d.items() if k in ['Id', 'Image', 'Created']}
        n_d['ip'] = ip
        n_d['port'] = port
        return n_d

    ''' This needs to hit our open servers collection, and return it.'''

    def get(self):
        # We need to grab paging information
        # args = self.__parse_get_args()
        # limit = 250
        # Filter out all containers with game name "game-server" and pull ids
        # Later, this should come from an evironment variable
        image = 'ibm/game-server'
        containers = [c for c in docker.containers() if c['Image'] == image]
        srvrs = [GameServerList._minimal(c) for c in containers]
        game_info = [redis_client.hgetall(x['Id']) for x in srvrs]
        total_count = len(game_info)
        logging.critical(game_info)
        logging.info(game_info)
        logging.info(total_count)
        return {
            'success': True,
            'count': total_count,  # This is the amount in payload
            'servers': game_info
        }


class GameServerEndGame(Resource):
    # When we implement a lobby for the game, we will use this for
    # changing a game status to PLAY mode (when they click play)
    def post(self, game_id):
        try:
            redis_client.hset(g._game_id, "status", "DONE")
            return {
                'success': True,
            }
        except Exception:
            return {
                'success': False,
            }


class GameServerPlayGame(Resource):
    # When we implement a lobby for the game, we will use this for
    # changing a game status to PLAY mode (when they click play)
    def post(self, game_id):
        try:
            redis_client.hset(g._game_id, "status", "PLAY")
            return {
                'success': True,
            }
        except Exception:
            return {
                'success': False,
            }


class GameServerDisconnect(Resource):

    def _parse_get_args(self):
        gs_parser = reqparse.RequestParser()
        gs_parser.add_argument('port_num', type=int)
        return gs_parser.parse_args()

    def post(self, game_id):
        args = self._parse_get_args()
        logging.info("Attemtping to disconnect from game server")
        try:
            keys = ("max_connections", "total_connections",
                    "highest_number_connections", "status", "ip")
            # Pull game data
            raw_data = redis_client.hmget(game_id, keys)
            # Package content as dictionary
            conn_data = dict(zip(keys, raw_data))
            new_total_conn = int(conn_data["total_connections"]) - 1
            logging.info("{0}: New Number of Connections - {1}".format(game_id, new_total_conn))
            # Remove the user from the routing table first
            redis_client.hdel(app.config['ROUTING_STORE'], ":".join([extract_source_ip(), str(args['port_num'])]))
            # Removed from routing table, now publish the update to forwarders
            # TODO MAKE THIS AN ENV VARIABLE [UPDATE_CHANNEL_NAME]
            redis_client.publish('routing_updates', json.dumps({"key": ":".join([extract_source_ip(), str(args['port_num'])]),
                                                                "s_ip": extract_source_ip(),
                                                                "s_port": str(args['port_num']),
                                                                "d_ip": conn_data,
                                                                "d_port": app.config['GAME_PORT'],
                                                                "action": "DISC",
                                                                }))
            if new_total_conn == 0 and int(conn_data["highest_number_connections"]):
                # Delete the game info from redis
                redis_client.delete(game_id)
                # Kill actual game server
                docker.remove_container(game_id, force=True)
                return {
                    "success": True,
                    "update": {
                        "total_connections": 0
                    }
                }
            else:
                update = {
                    "total_connections": max(0, new_total_conn)
                }
                # Push the connection update to redis
                redis_client.hmset(game_id, update)
                new_data = redis_client.hgetall(game_id)
                return {
                    "success": True,
                    "game_id": game_id,
                    "current": {k: v for k, v in new_data.items() if v is not None}
                }
        except Exception:
            logging.critical(traceback.format_exc())
            return {
                "success": False,
                "error": "Unable to connect to service discovery."
            }


class GameServerConnect(Resource):
    def _parse_get_args(self):
        gs_parser = reqparse.RequestParser()
        gs_parser.add_argument('port_num', type=int)
        return gs_parser.parse_args()

    def is_not_joinable(self, conn_data):
        return conn_data['status'] == 'WAIT' and conn_data['total_connections'] >= conn_data['max_connections']

    def _redis_connect_transaction(self, pipe):
        keys = ("ip", "port", "max_connections", "total_connections",
                "highest_number_connections", "status", "server_id")
        args = self._parse_get_args()
        try:
            raw_data = pipe.hmget(g._game_id, keys)
            logging.debug("raw_data")
            logging.debug(raw_data)
            conn_data = dict(zip(keys, raw_data))
            logging.debug("conn_data")
            logging.debug(conn_data)
            if self.is_not_joinable(conn_data):
                return {
                    'success': False,
                    'error': "Server is already at capacity"
                }
            else:
                update = {
                    "total_connections": int(conn_data['total_connections']) + 1,
                    "highest_number_connections": min(int(conn_data['max_connections']),
                                                      int(conn_data['highest_number_connections']) + 1)

                }
                logging.debug("update")
                logging.debug(update)
                pipe.multi()
                pipe.hmset(g._game_id, update)
                pipe.hset(app.config['ROUTING_STORE'],
                          ":".join([extract_source_ip(), str(args['port_num'])]),
                          ":".join([conn_data['ip'], conn_data['port'], g._game_id]))
                # TODO MAKE THIS AN ENV VARIABLE [UPDATE_CHANNEL_NAME]
                pipe.publish('routing_updates', json.dumps({"key": ":".join([extract_source_ip(), str(args['port_num'])]),
                                                            "s_ip": extract_source_ip(),
                                                            "s_port": str(args['port_num']),
                                                            "d_ip": conn_data['ip'],
                                                            "d_port": app.config['GAME_PORT'],
                                                            "id": conn_data['server_id'],
                                                            "action": "CONN",
                                                            }))
                pipe.execute()
                new_data = redis_client.hgetall(g._game_id)
                return {
                    "success": True,
                    "game_id": g._game_id,
                    "current": {k: v for k, v in new_data.items() if v is not None}
                }
        except Exception:
            logging.critical(traceback.format_exc())
            return {
                "success": False,
                "error": "Unable to connect to service discovery."
            }

    def post(self, game_id):
        # This call updates our game server by adding a new connection to the log
        # This call also adds our player's IP to a specified routing table
        g._game_id = game_id
        result = redis_client.transaction(self._redis_connect_transaction, game_id, value_from_callable=True)
        logging.debug("result")
        logging.debug(result)
        return result


class GameServer(Resource):

    def __parse_post_args(self):
        logging.critical("building arg parser")
        logging.critical(request.data)
        logging.critical(request.get_json())
        logging.critical(request.headers)
        gs_parser = reqparse.RequestParser()
        gs_parser.add_argument("name", type=str, required=True)
        gs_parser.add_argument("host", type=str, required=False)
        gs_parser.add_argument("max_connections", type=str, required=True)
        gs_parser.add_argument("game_fields", type=dict, required=True)
        logging.critical("finished building arg parser")
        return gs_parser.parse_args()

    def get(self, game_id):
        try:
            game_info = redis_client.hgetall(game_id)
            data = game_info
            return {"success": True,
                    "game_data": {k: v for k, v in data.items() if v is not None}
                    }
        except Exception:
            logging.critical(traceback.format_exc())
            return {
                "success": False,
                "error": "Unable to connect to service discovery"
            }

    # Create new game server on cluster
    def post(self):
        # Need to parse through POST data, create container, start container
        # create json info for server, then post to redis, and send data back
        # to player to automatically connect to server.
        logging.critical("Attempting to add new game server")
        args = self.__parse_post_args()
        logging.critical(args)
        if all([args.get('name'), args.get('max_connections'), args.get('game_fields')]):
            try:
                args['max_connections'] = int(args['max_connections'])
                # Create our game server container
                g = docker.create_container(image="ibm/game-server")
                # Attempt to start container (we know we are listening on 7777)
                # We want our game to be in the private network
                resp = docker.start(container=g.get('Id'))
                if not resp:
                    # Lets create our redis info, and return game data to player
                    # client.port(): a list of dict {HostIP: IP, HostPort:
                    # Port}
                    net_nfo = docker.inspect_container(g.get('Id'))["NetworkSettings"]
                    print(net_nfo)
                    # Generate redis key to store game info in redis
                    args['server_id'] = g['Id']
                    args['ip'] = net_nfo['IPAddress']
                    args['port'] = app.config['GAME_PORT']
                    # Make this zero. A second command to connect to this
                    # server will be made
                    args['total_connections'] = 0
                    # This will keep track of the most connections the server
                    # has seen
                    args['highest_number_connections'] = 0
                    # This will keep track of server status
                    args['status'] = 'WAIT'
                    # Save our game information in a Redis hashmap with key
                    if redis_client.hmset(g['Id'], args):
                        print(args)
                        return {
                            'success': True,
                            # Filtering out any null values...
                            'game_data': {k: v for k, v in args.items() if v is not None}
                        }
                    else:
                        # We need to kill the container, as we are unable to access
                        # service discovery (redis or etcd)
                        docker.remove_container(g.get('Id'), force=True)
                        print("SUCCESS: False")
                        return {
                            'success': False,
                            'error': "Game Server created, but unable to connect to service discovery. Terminated server."
                        }
                else:
                    raise ValueError("Invalid response from relay.")
            except Exception:
                logging.critical(traceback.format_exc())
                print("SUCCESS: False")
                return {
                    'success': False,
                    'error': "Internal server error. Unable to create game."
                }
        else:
            logging.critical(traceback.format_exc())
            return {
                'success': False,
                'error': 'Missing name, host, and max_players from payload'
            }
