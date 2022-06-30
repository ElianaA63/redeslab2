# encoding: utf-8
# Revisión 2019 (a Python 3 y base64): Pablo Ventura
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

from socket import *
from os import listdir
from os.path import isfile, getsize
from constants import *
from base64 import b64encode


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """
#inicializamos nuestras herramientas
    def _init_(self, socket, directory):
        self.socket = socket
        self.directory = directory
        self.buffer = ""
        self.status = CODE_OK
        self.closed = False

#método para recibir info del socket
    def _recv(self, socket):
        #recibimos hasta 4096 bytes
        #decode xq con recv los datos resultan en bytes y necesitamos decodificarlo de ascii
        data = socket.recv(4096).decode("ascii")
        #lo que recibimos lo agregamos al bufer
        self.buffer += data
        #verificamos que NO existan \n o \r en el bufer
        if not self._check_data(self.buffer):
            #vemos estado de socket
            self._send_status()

    def _check_data(self, b):
     #El startswith()método devuelve True si la cadena comienza con el valor especificado;
     # de lo contrario, Falso.   
        #si el bufer comienza con \n o \r o ' ' 
        if b.startswith('\n') or b.startswith('\r') or b.startswith(' '):
            #es un mal pedido
            self.status = BAD_REQUEST
            #vemos estado de socket
            self._send_status()
            return False
        #si hay un \n y no un \r\n
        elif '\n' in b and not EOL in b:
            self.status = BAD_EOL
            self._send_status()
            return False
        return True

#método para ver el estado del socket
    def _send_status(self):
        try:
            #si es un estado valido(ver constants.py)
            if(valid_status(self.status)):
                #enviamos por el socket el estado seguido del mensaje de error y el EOL
                #encode(ascii) xq lo pasamos a ASCII
                self.socket.send((str(self.status) + ' ' +
                                  error_messages[self.status] + EOL).encode('ascii'))
                #si el estado es BAD_EOL/REQUEST o INTERNAL_ERROR
                if self.status > 99 and self.status < 200:
                    #vamos a cerrar el socket
                    self.closed = True
                    #efectivamente cerramos
                    self.socket.close()
            #sino, es un error interno
            else:
                self.status = INTERNAL_ERROR
                #mandamos el estado seguido del mensaje de error y EOL
                self.socket.send((str(self.status) + ' ' +
                                  error_messages[self.status] + EOL).encode('ascii'))
                #y marcamos que podemos cerrar el socket
                self.closed = True
        #si es una falla con respecto al sistema o I/O cerramos socket de cliente
        except socket.error:
            print('Client socket closed')
            self.closed = True

#método que se encarga de enviar el mensaje recibido, 
# en caso de error, cierra el socket del cliente
    def _send_message(self, message):
        try:
            self.socket.send(message)
        except socket.error:
            print('Client socket closed')
            self.closed = True

#método que devuelve una lista de archivos del directorio actual.
    def _only_files(self):
        #creamos una lista vacía
        files = []
        #obtenemos la lista de todos los archivos y directorios en el directorio especificado
        #con join convertimos la lista en cadena de texto
        dirs = listdir(os.path.join(self.directory))
        #esto es para debug: import ipdb;ipdb.set_trace()
        #dir = i
        for dir in dirs:
            #si i es un archivo
            if isfile(os.path.join(DEFAULT_DIR,dir)):
                #lo agregamos a la lista "files"
                files.append(dir)
        return files

#método para ver si podemos convertir 2 strings en enteros
    def _check(self, str1, str2):
        try:
            str1 = int(str1)
            str2 = int(str2)
            return True
        except ValueError:
            return False

#Con éste método trabajamos con el comando recibido a través del búfer,
#  como una lista. Según el "parseo" del comando, ejecutará el correspondiente,
#  sino el soket cerrará o continuará.
    def _parser(self):
        #del bufer, separamos el comando recibido, por EOL 1 vez, resultando una lista de comandos
        command, self.buffer = self.buffer.split(EOL, 1)
        #al comando le quitamos los primeros y finales espacios en blanco con strip
        command = command.strip()
        #verificamos si existen \n o \r o ' ' en el comando
        self._check_data(command)
        #creamos una lista de comandos
        lis_command = []

        if ' ' in command:
            #quitamos ' ' del comando y lo guardamos en nuestra lista
            lis_command = command.split(' ')
            #ahora mi comando va a ser el primer argumento
            command = lis_command[0]
        leng = len(lis_command)
        #si el comando a quit
        if 'quit' == command:
            #si la longuitud del comando es más de una palabra
            if leng > 0:
                #entonces está mal, quit va sin argumentos
                self.status = INVALID_ARGUMENTS
                self._send_status()
            #si está todo joia
            else:
                #estado de socket es correcto
                self.status = CODE_OK
                #mando el estado del socket
                self._send_status()
                #cierro el socket
                self.closed = True
        #si el comando es get_file_listing
        elif 'get_file_listing' == command:
            #si tiene argumentos
            if leng > 0:
                #está mal, no lleva argumentos
                self.status = INVALID_ARGUMENTS
                self._send_status()
            #si está todo joia
            else:
                #estado de socket es correcto
                self.status = CODE_OK
                #mando estado de socket
                self._send_status()
                #obtengo los archivos del directorio donde estoy
                files = self._only_files()
                #para cada archivo
                for file in files:
                    #guardo en 'send' el archivo como string seguido de EOL pero en ascii
                    send = (str(file) + ' ' + EOL).encode('ascii')
                    #mando como mensaje a 'send' por el socket
                    self._send_message(send)
                #mando el fin de linea en ascii por el socket
                self._send_message(EOL.encode('ascii'))
        #si mi comando es get_metadata
        elif 'get_metadata' == command:
            #y son comando + nombre_archivo
            if leng == 2:
                #el nombre de archivo es la siguiente posicion en la lista
                filename = lis_command[1]
                #obtengo todos los archivos del directorio en donde estoy
                files = self._only_files()
                #si el nombre de archivo existe entre todos esos archivos
                if filename in files:
                    #el estado del socket es correcto
                    self.status = CODE_OK
                    #mando estado de socket
                    self._send_status()
                    #guardo en size el tamaño del archivo
                    size = getsize(os.path.join(DEFAULT_DIR, filename))
                    #guardo en send ese size, pero como string seguido de EOL, codificado en ascii
                    send = (str(size) + EOL).encode('ascii')
                    #mando send por el socket
                    self._send_message(send)
                
                #si es comando + nombre_archivo pero no existe ese nombre
                else:
                    self.status = FILE_NOT_FOUND
                    self._send_status()
            
            #si no es de longitud 2
            else:
                self.status = INVALID_ARGUMENTS
                self._send_status()
        #si el comandoes get_slice
        elif 'get_slice' == command:
            #si es comando+nombre_archivo+offset+size
            if leng == 4:
                #esta línea resulta: command = lis_command[0], filename=lis_command[1]
                # offset=lis_command[2] y size=lis_command[3]
                command, filename, offset, size = lis_command
                #si puedo convertir offset y size en enteros
                if self._check(offset, size):
                    #los convierto a enteros
                    offset = int(offset)
                    size = int(size)
                    #si existe nombre_archivo en la lista de archivos
                    if filename in self._only_files():
                        #obtengo el tamaño de archivo
                        size_file = getsize(os.path.join(DEFAULT_DIR, filename))
                        #variable con la longitud de hasta donde quiero mostrar del archivo
                        length = offset + size
                        #si la longitud está entre 0 y el tamaño del archivo
                        if length <= size_file and length >= 0:
                            #estado del socket es correcto
                            self.status = CODE_OK
                            #mando estado del socket
                            self._send_status()
                            #abro el archivo en modo lectura(r) en formato binario(b)
                            file = open(os.path.join(DEFAULT_DIR, filename), 'rb')
                            #guardo acá la lectura del archivo
                            response = file.read()
                            #la lectura será desde el offset hasta [offset+size]
                            response = response[offset:(offset+size)]
                            #cierro el archivo
                            file.close()
                            #ahora a la lectura le convertimos los datos binarios a "texto" seguro para ASCII
                            response = b64encode(response)
                            #mandamos esa lectura por el socket
                            self._send_message(response)
                            #mandamos el 'fin de linea' por el socket como ascii
                            self._send_message(EOL.encode('ascii'))
                        
                        #si la longitud no está dentro de 0 y el tamaño total del archivo
                        else:
                            self.status = BAD_OFFSET
                            self._send_status()

                    #si no existe el nombre_archivo en la lista de archivos
                    else:
                        self.status = FILE_NOT_FOUND
                        self._send_status()
                
                #si no los pude convertir en enteros => args inválidos
                else:
                    self.status = INVALID_ARGUMENTS
                    self._send_status()

            #si no es de tamaño 4 => argumentos invalidos
            else:
                self.status = INVALID_ARGUMENTS
                self._send_status()

        #si no es NINGUNO de esos comandos anteriores
        else:
            self.status = INVALID_COMMAND
            self._send_status()

#este método es quien se hace cargo de lo que ocurra en la conexión
    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        #mientras el socket esté abierto
        while not self.closed:
            #y mientras no nos encontremos con un 'fin de linea' en el bufer
            while not EOL in self.buffer:
                #voy a recibir todos datos que se estén mandando por el socket
                self._recv(self.socket)
            #cuando termine de recibir lo que se mande por el socket
            # (en especial el cliente), veo que hay que hacer
            self._parser()