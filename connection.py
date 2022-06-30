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

    def __init__(self, socket, directory):
        self.socket = socket
        self.directory = directory
        self.buffer = ""
        self.status = CODE_OK
        self.closed = False

    def _recv(self, socket):
        data = socket.recv(4096).decode("ascii")
        self.buffer += data
        if not self._check_data(self.buffer):
            self._send_status()

    def _check_data(self, b):
        if b.startswith('\n') or b.startswith('\r') or b.startswith(' '):
            self.status = BAD_REQUEST
            self._send_status()
            return False
        elif '\n' in b and not EOL in b:
            self.status = BAD_EOL
            self._send_status()
            return False
        return True

    def _send_status(self):
        try:
            if(valid_status(self.status)):
                self.socket.send((str(self.status) + ' ' +
                                  error_messages[self.status] + EOL).encode('ascii'))
                if self.status > 99 and self.status < 200:
                    self.closed = True
                    self.socket.close()
            else:
                self.status = INTERNAL_ERROR
                self.socket.send((str(self.status) + ' ' +
                                  error_messages[self.status] + EOL).encode('ascii'))
                self.closed = True
        except socket.error:
            print('Client socket closed')
            self.closed = True

    def _send_message(self, message):
        try:
            self.socket.send(message)
        except socket.error:
            print('Client socket closed')
            self.closed = True

    def _only_files(self):
        files = []
        dirs = listdir(os.path.join(self.directory))
        #import ipdb;ipdb.set_trace()
        for dir in dirs:
            if isfile(os.path.join(DEFAULT_DIR,dir)):
                files.append(dir)
        return files

    def _check(self, str1, str2):
        try:
            str1 = int(str1)
            str2 = int(str2)
            return True
        except ValueError:
            return False

    def _parser(self):
        command, self.buffer = self.buffer.split(EOL, 1)
        command = command.strip()
        self._check_data(command)
        lis_command = []

        if ' ' in command:
            lis_command = command.split(' ')
            command = lis_command[0]
        leng = len(lis_command)

        if 'quit' == command:
            if leng > 0:
                self.status = INVALID_ARGUMENTS
                self._send_status()

            else:
                self.status = CODE_OK
                self._send_status()
                self.closed = True

        elif 'get_file_listing' == command:
            if leng > 0:
                self.status = INVALID_ARGUMENTS
                self._send_status()

            else:
                self.status = CODE_OK
                self._send_status()
                files = self._only_files()
                for file in files:
                    send = (str(file) + ' ' + EOL).encode('ascii')
                    self._send_message(send)
                self._send_message(EOL.encode('ascii'))

        elif 'get_metadata' == command:
            if leng == 2:
                filename = lis_command[1]
                files = self._only_files()
                if filename in files:
                    self.status = CODE_OK
                    self._send_status()
                    size = getsize(os.path.join(DEFAULT_DIR, filename))
                    send = (str(size) + EOL).encode('ascii')
                    self._send_message(send)

                else:
                    self.status = FILE_NOT_FOUND
                    self._send_status()

            else:
                self.status = INVALID_ARGUMENTS
                self._send_status()

        elif 'get_slice' == command:
            if leng == 4:
                command, filename, offset, size = lis_command
                if self._check(offset, size):
                    offset = int(offset)
                    size = int(size)
                    if filename in self._only_files():
                        size_file = getsize(os.path.join(DEFAULT_DIR, filename))
                        length = offset + size
                        if length <= size_file and length >= 0:
                            self.status = CODE_OK
                            self._send_status()
                            file = open(os.path.join(DEFAULT_DIR, filename), 'rb')
                            response = file.read()
                            response = response[offset:(offset+size)]
                            file.close()
                            response = b64encode(response)
                            self._send_message(response)
                            self._send_message(EOL.encode('ascii'))

                        else:
                            self.status = BAD_OFFSET
                            self._send_status()

                    else:
                        self.status = FILE_NOT_FOUND
                        self._send_status()

                else:
                    self.status = INVALID_ARGUMENTS
                    self._send_status()

            else:
                self.status = INVALID_ARGUMENTS
                self._send_status()

        else:
            self.status = INVALID_COMMAND
            self._send_status()

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        while not self.closed:
            while not EOL in self.buffer:
                self._recv(self.socket)
            self._parser()
