import cherrypy
from app import app, api
from models import GameServer, GameServerList, GameServerConnect, GameServerDisconnect


def add_resources():
    # We will add our resources here
    api.add_resource(GameServer, "/games/server", "/games/server/<game_id>")
    api.add_resource(GameServerList, "/games/list")
    api.add_resource(GameServerConnect, "/games/server/<game_id>/connect")
    api.add_resource(GameServerDisconnect, "/games/server/<game_id>/disconnect")
    print("Added resources")


# This is the cherrypy server that will run our flask app gamerelay
def run_server():
    add_resources()
    cherrypy.tree.graft(app, "/")

    cherrypy.config.update({
        'server.socket_host': '0.0.0.0',
        'server.socket_port': 8080
    })

    cherrypy.engine.start()
    cherrypy.engine.block()


if __name__ == "__main__":
    run_server()
