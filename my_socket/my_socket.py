#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""CTS socket
   by Kobe Gong. 2017-4-21
"""

import time, sys, re, os
import datetime
import queue
import socket
import select
from log_tool.log_tool import my_logging
import logging

log_handle = my_logging(__name__ + ".log", clevel=logging.INFO, flevel=logging.INFO)

class my_server:
    def __init__(self, addr, data_centre):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setblocking(False)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(addr)
        server.listen(50)
        self.server = server           
        self.data_centre = data_centre

    def run_forever(self):
        epoll = select.epoll()
        epoll.register(self.server.fileno(), select.EPOLLIN | select.EPOLLHUP)
        timeout = 0.1
        BUFF_SIZE = 1024
        fileno_to_addr = {}

        try:
            while True:
                log_handle.p.debug("Waiting for next event")
                events = epoll.poll(timeout)

                # When timeout reached , select return three empty lists
                if not (events):                  
                    pass

                for fileno, event in events:
                    if fileno == self.server.fileno():
                        try:
                            connection, client_address = self.server.accept()
                            connection.setblocking(0)
                            if self.data_centre.node_resource.is_available_node(client_address[0]):
                                fileno_to_addr[connection.fileno()] = client_address[0]
                                self.data_centre.node_resource.set_conn(fileno_to_addr[connection.fileno()], connection)
                                self.data_centre.node_resource.set_node_state(fileno_to_addr[connection.fileno()], 'active')
                                epoll.register(connection.fileno(), select.EPOLLIN)
                                log_handle.p.info("Get connection from " + client_address[0]) 
                            else:
                                log_handle.p.info("Get connection from inavailable node: " + client_address[0])

                        except socket.error:
                            log_handle.p.error("Get connection falied!" + fileno + event) 
                            pass

                    elif event & select.EPOLLIN:
                        try:
                            data = self.data_centre.node_resource.get_conn(fileno_to_addr[fileno]).recv(BUFF_SIZE).decode(encoding='utf-8')
                            if data:
                                self.data_centre.node_resource.add_data_in(fileno_to_addr[fileno], data)
                                log_handle.p.info("Get data from " + fileno_to_addr[fileno] + ": " + data)
                            else:
                                #Interpret empty result as closed connection
                                log_handle.p.error(fileno_to_addr[fileno] + ' closed!') 
                                epoll.unregister(fileno)
                                self.data_centre.node_resource.get_conn(fileno_to_addr[fileno]).close()
                                self.data_centre.node_resource.set_node_state(fileno_to_addr[fileno], 'dead')
                                del fileno_to_addr[fileno]
                                    
                        except socket.error:
                            log_handle.p.error("Get data falied!") 
                            pass                            
                                    
                    elif event & select.EPOLLHUP:
                        epoll.unregister(fileno)                    
                        self.data_centre.node_resource.get_conn(fileno_to_addr[fileno]).close()
                        self.data_centre.node_resource.set_node_state(fileno_to_addr[fileno], 'dead')
                        del fileno_to_addr[fileno]
                        
                for fileno in fileno_to_addr:
                    if self.data_centre.node_resource.data_out_is_empty(fileno_to_addr[fileno]):
                        log_handle.p.debug("No data need send to client: " + str(self.data_centre.node_resource.get_hostname(fileno_to_addr[fileno])))
                        pass
                    else:
                        data = self.data_centre.node_resource.get_data_out(fileno_to_addr[fileno])                                          
                        self.data_centre.node_resource.get_conn(fileno_to_addr[fileno]).send(str(data).encode('utf-8'))
                        log_handle.p.info("Send data to " + self.data_centre.node_resource.get_hostname(fileno_to_addr[fileno]) + ": " + str(data))

        except KeyboardInterrupt:
            for client in self.clients:
                self.data_centre.node_resource.get_conn(fileno_to_addr[fileno]).close()
            self.server.close()

        finally:
            print ("End!")
            epoll.unregister(self.server.fileno())
            epoll.close()


class my_client:
    def __init__(self, addr, in_queue, out_queue):  
        self.queue = {
            'in' : in_queue,
            'out': out_queue,
        }
        self.addr = addr

    def run_forever(self):
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client = client

        while not self.queue['in'].empty():
            self.queue['in'].get_nowait()

        while not self.queue['out'].empty():
            self.queue['out'].get_nowait()

        while True:
            try:
                self.client.connect(self.addr)
                log_handle.p.info("Connection setup suceess!")
                while not self.queue['in'].empty():
                    self.queue['in'].get_nowait()

                while not self.queue['out'].empty():
                    self.queue['out'].get_nowait()
                break
            except ConnectionRefusedError:
                log_handle.p.warning("Connect to server failed, wait 10s...")   
                time.sleep(10)   

        epoll = select.epoll()
        epoll.register(self.client.fileno(), select.EPOLLIN | select.EPOLLERR | select.EPOLLHUP)
        timeout = 0.1
        BUFF_SIZE = 1024

        try:
            while True:
                events = epoll.poll(timeout)

                # When timeout reached , select return three empty lists
                if not (events):
                    log_handle.p.debug("No data recived!")
                    pass

                for fileno, event in events:
                    if fileno == self.client.fileno():
                        try:
                            data = self.client.recv(BUFF_SIZE).decode(encoding='utf-8')
                            if data:
                                self.queue['in'].put(data)
                                
                                #These 2 lines just for debug server use
                                #data2 = data.strip() + '-fail '
                                #self.queue['out'].put(data2)
                                log_handle.p.info("client get data: %s" % (data))

                            else:
                                #Interpret empty result as closed connection
                                epoll.unregister(fileno)
                                self.client.close()
                                log_handle.p.error("Server maybe has closed!")
                                return

                        except socket.error:
                            log_handle.p.error("socket error, don't know why.")
                                                          
                    elif event & select.EPOLLHUP or event & select.EPOLLERR:
                        epoll.unregister(fileno)
                        self.client.close()
                        log_handle.p.error("socket closed.")
                        return

                if self.queue['out'].empty():
                    log_handle.p.debug("client no data to send!")    
                    pass
                else:
                    data = self.queue['out'].get()
                    log_handle.p.info("client send date: %s" % (data))
                    self.client.send(data.encode('utf-8'))

        except KeyboardInterrupt:
            self.client.close()
            log_handle.p.warning("Oh, you killed me...")
            sys.exit(0)

        except:     
            self.client.close()
            log_handle.p.error("server socket closed.")

        finally:
            log_handle.p.info("End!")
            epoll.close()

        
        
        
        
        
        
        

