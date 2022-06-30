#!/usr/bin/env python
# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import optparse
import socket
from connection import *
import sys
from constants import *
from socket import *
from _thread import start_new_thread

class Server(object):
    """
    El servidor, que crea y atiende el socket en la dirección y puerto
    especificados donde se reciben nuevas conexiones de clientes.
    """

    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        print("Serving %s on %s:%s." % (directory, addr, port))
        # FALTA: Crear socket del servidor, configurarlo, asignarlo
        # a una dirección y puerto, etc.
        self.s = socket(AF_INET, SOCK_STREAM) #socket que sirve de server
        self.s.bind((addr, port))             #se vincula con la direccion y puerto
        self.s.listen(5)                      #escucha peticiones de conexion
        self.directory = directory

    def _client_thread(self, connection_socket):
        conn = Connection(connection_socket, self.directory)
        conn.handle()
        connection_socket.close()

    def serve(self):
        """
        Loop principal del servidor. Se acepta una conexión a la vez
        y se espera a que concluya antes de seguir.
        """
        # FALTA: Aceptar una conexión al server, crear una
        # Connection para la conexión y atenderla hasta que termine.
        while True:
            try:
                connection_socket, addr = self.s.accept()
                print ("Connection from %s\n" % addr[0])
                conn = Connection(connection_socket, self.directory)
                conn.handle()
                connection_socket.close()
                #try:
                #    start_new_thread(self._client_thread(connection_socket), ('',''))
                #except:
                #    print ("Error: unable to start thread")

            except KeyboardInterrupt:
                connection_socket.close()
                break
            except:
                print("Conexion no establecida o perdida")
            
            
def main():
    """Parsea los argumentos y lanza el server"""

    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help="Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help="Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help="Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write(
            "Numero de puerto invalido: %s\n" % repr(options.port))
        parser.print_help()
        sys.exit(1)

    server = Server(options.address, port, options.datadir)
    server.serve()


if __name__ == '__main__':
    main()
