!/usr/bin/env python
# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Revisiones 2013-2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: client.py 387 2011-03-22 13:48:44Z nicolasw $

import socket
import logging
import optparse
import sys
import time
from base64 import b64decode
from constants import *


class Client(object):

    def _init_(self, server=DEFAULT_ADDR, port=DEFAULT_PORT):
        """
        Nuevo cliente, conectado al `server' solicitado en el `port' TCP
        indicado.

        Si falla la conexión, genera una excepción de socket.
        """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.status = None
        self.s.connect((server, port))
        self.buffer = ''
        self.connected = True

    def close(self):
        """
        Desconecta al cliente del server, mandando el mensaje apropiado
        antes de desconectar.
        """
        #manda comando quit
        self.send('quit')
        #espera y parsea la respuesta al comando
        self.status, message = self.read_response_line()
        #si el status no es de 'todo joia'
        if self.status != CODE_OK:
            logging.warning("Warning: quit no contesto ok, sino '%s'(%s)'."
                            % (message, self.status))
        #la conexion ya no existe
        self.connected = False
        #cliente cierra su socket
        self.s.close()

    def send(self, message, timeout=None):
        """
        Envía el mensaje 'message' al server, seguido por el terminador de
        línea del protocolo.

        Si se da un timeout, puede abortar con una excepción socket.timeout.

        También puede fallar con otras excepciones de socket.
        """
        #Establece un tiempo de espera para bloquear las operaciones de socket.
        self.s.settimeout(timeout)
        message += EOL  # Completar el mensaje con un fin de línea
        while message:
            logging.debug("Enviando el (resto del) mensaje %s."
                          % repr(message))
            #manda el mensaje codificado en ascii
            bytes_sent = self.s.send(message.encode("ascii"))
            assert bytes_sent > 0
            #mensaje ahora son los bytes mandados
            message = message[bytes_sent:]

    def _recv(self, timeout=None):
        """
        Recibe datos y acumula en el buffer interno.

        Para uso privado del cliente.
        """
        #Establece un tiempo de espera para bloquear las operaciones de socket
        self.s.settimeout(timeout)
        #en data guarda todo lo que reciba del socket, decodificado en ascii
        data = self.s.recv(4096).decode("ascii")
        #guarda en su bufer esos datos recibidos
        self.buffer += data
        #si la longitud del dato es 0
        if len(data) == 0:
            logging.info("El server interrumpió la conexión.")
            #la conexion no existe
            self.connected = False

    def read_line(self, timeout=None):
        """
        Espera datos hasta obtener una línea completa delimitada por el
        terminador del protocolo.

        Devuelve la línea, eliminando el terminaodr y los espacios en blanco
        al principio y al final.
        """
        #mientras no haya 'fin de linea' y la conexion exista
        while not EOL in self.buffer and self.connected:
            #si aún hay tiempo
            if timeout is not None:
                #guardamos en t1 el valor flotante del tiempo en segundos
                t1 = time.process_time()
            #recibe datos segun el tiempo?    
            self._recv(timeout)
            #si aun hay tiempo
            if timeout is not None:
                #en t2 gurado el valor flotante del tiempo en segundos
                t2 = time.process_time()
                #actualizo timeout en t2-t1-1
                timeout -= t2 - t1
                #ahora actualizo t1
                t1 = t2
        #si hay EOL en elbufer        
        if EOL in self.buffer:
            #del bufer, separamos la linea de respuesta recibida, por EOL 1 vez, resultando una lista con respuestas
            response, self.buffer = self.buffer.split(EOL, 1)
            #devuelvo la linea de respuesta sin los espacios del principio y del final
            return response.strip()
        #si no hay EOL en el bufer
        else:
            #la conexion no existe
            self.connected = False
            #devuelvo una línea de respuesta vacía
            return ""

    def read_response_line(self, timeout=None):
        """
        Espera y parsea una línea de respuesta de un comando.

        Devuelve un par (int, str) con el código y el error, o
        (None, None) en caso de error.
        """
        #result es una tupla (None, None)
        result = None, None
        #obtengo la linea de respuesta en cierto tiempo
        # #es decir, esperamos hasta tener la cantidad de datos necesaria en un tiempo determinado 
        response = self.read_line(timeout)
        #si hay espacio en blanco en esa linea
        if ' ' in response:
            #quito los espacios en blanco
            code, message = response.split(None, 1)
            try:
                #ahora result será una tupla (nro de codigo, mensaje)
                result = int(code), message
            except ValueError:
                #si hay error con los valores, tranca pasa de largo
                pass
        #Si no hay espacios en blanco
        else:
            logging.warning("Respuesta inválida: '%s'" % response)
        #devuelvo la tupla result=(nro codigo, mensaje)o (None, None) en caso de error
        return result

    def read_fragment(self, length):
        """
        Espera y lee un fragmento de un archivo.

        Devuelve el contenido del fragmento.
        """
        # Ahora, esperamos hasta tener la cantidad de datos necesaria
        data = self.read_line()
        #convertimos los datos binarios a "texto" para ascii
        fragment = b64decode(data)
        #mientras la longitud del frangmento sea menor a la del archivo
        while len(fragment) < length:
            #esperamos hasta tener la cant. de datos necesaria
            data = self.read_line()
            #y los agregamos al fragmento pero convertidos
            fragment += b64decode(data)
        #devuelvo el contenido del fragmento
        return fragment

    def file_lookup(self):
        """
        Obtener el listado de archivos en el server. Devuelve una lista
        de strings.
        """
        #creamos lista vacia de result
        result = []
        #mando el comando 'get_file_listing'
        self.send('get_file_listing')
        #obtengo el código y su mensaje (o (None, None) en caso de error)
        self.status, message = self.read_response_line()
        #si el codigo de estado es 0
        if self.status == CODE_OK:
            #esperamos hasta tener la cant. de datos necesaria
            #es decir, esperamos un nombre de archivo
            filename = self.read_line()
            #mientras siga recibiendo nombres de archivo
            while filename:
                logging.debug("Received filename %s" % filename)
                #los voy agregando a la lista result
                result.append(filename)
                #obtengo el siguiente nombre de archivo
                filename = self.read_line()
        #si el codigo de estado no es 0
        else:
            logging.warning("Falló la solicitud de la lista de archivos" +
                            "(code=%s %s)." % (self.status, message))
        #devuelvo la lista vacia o con nombres de archivos
        return result

    def get_metadata(self, filename):
        """
        Obtiene en el server el tamaño del archivo con el nombre dado.
        Devuelve None en caso de error.
        """
        #mando el comando "get_metadata" seguido de un nombre de archivo
        self.send('get_metadata %s' % filename)
        #obtengo el par codigo y mensaje como respuesta del comando
        self.status, message = self.read_response_line()
        #si el codigo es 0
        if self.status == CODE_OK:
            #convierto a entero el dato recibido
            size = int(self.read_line())
            return size

    def get_slice(self, filename, start, length):
        """
        Obtiene un trozo de un archivo en el server.

        El archivo es guardado localmente, en el directorio actual, con el
        mismo nombre que tiene en el server.
        """
        #mando el comando get_slice con 3 argumentos más
        self.send('get_slice %s %d %d' % (filename, start, length))
        #obtengo el codigo y mensaje como respuesta al comando
        self.status, message = self.read_response_line()
        #si el codigo de estado es 0
        if self.status == CODE_OK:
            #abro el archivo con permiso de escritura(w) en formato binario(b)
            output = open(filename, 'wb')
            #obtengo el contenido del fragmento 
            fragment = self.read_fragment(length)
            #escribo ese fragmento
            output.write(fragment)
            #cierro output
            output.close()
        else:
            logging.warning("El servidor indico un error al leer de %s."
                            % filename)

    def retrieve(self, filename):
        """
        Obtiene un archivo completo desde el servidor.
        """
        #obtengo el tamano de un archivo en el server
        size = self.get_metadata(filename)
        #si está todo joia en el socket
        if self.status == CODE_OK:
            assert size >= 0
            #tomo el fragmento de ese archivo desde el principio al final
            self.get_slice(filename, 0, size)
        elif self.status == FILE_NOT_FOUND:
            logging.info("El archivo solicitado no existe.")
        else:
            logging.warning("No se pudo obtener el archivo %s (code=%s)."
                            % (filename, self.status))


def main():
    """
    Interfaz interactiva simple para el cliente: permite elegir un archivo
    y bajarlo.
    """
    DEBUG_LEVELS = {'DEBUG': logging.DEBUG,
                    'INFO': logging.INFO,
                    'WARN': logging.WARNING,
                    'ERROR': logging.ERROR,
                    }

    # Parsear argumentos
    parser = optparse.OptionParser(usage="%prog [options] server")
    parser.add_option("-p", "--port",
                      help="Numero de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option("-v", "--verbose", dest="level", action="store",
                      help="Determina cuanta informacion de depuracion a mostrar"
                      "(valores posibles son: ERROR, WARN, INFO, DEBUG)",
                      default="ERROR")
    options, args = parser.parse_args()
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write("Numero de puerto invalido: %s\n"
                         % repr(options.port))
        parser.print_help()
        sys.exit(1)

    if len(args) != 1 or options.level not in list(DEBUG_LEVELS.keys()):
        parser.print_help()
        sys.exit(1)

    # Setar verbosidad
    code_level = DEBUG_LEVELS.get(options.level)  # convertir el str en codigo
    logging.getLogger().setLevel(code_level)

    try:
        #cliente se conecta al servidor y su puerto
        client = Client(args[0], port)
    #si no puede conectarse entonces except
    except(socket.error, socket.gaierror):
        sys.stderr.write("Error al conectarse\n")
        sys.exit(1)

    print("* Bienvenido al cliente HFTP - "
          "the Home-made File Transfer Protocol *\n"
          "* Estan disponibles los siguientes archivos:")
    #obtengo el listado de archivos en el server
    files = client.file_lookup()
    #imprimo todo esos archivos
    for filename in files:
        print(filename)
    #si el estado del cliente es 0
    if client.status == CODE_OK:
        print("* Indique el nombre del archivo a descargar:")
        #obtengo todo ese archivo pedido, caracteres en blanco al principio ni al final
        client.retrieve(input().strip())
    
    client.close()


if _name_ == '_main_':
    main()