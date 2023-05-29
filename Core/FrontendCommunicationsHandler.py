#!/usr/bin/env python3


import contextlib
from ast import literal_eval
from typing import Union
from pathlib import Path
from msgpack import loads, dumps
import socket
import threading
import time
import re
import networkx as nx

from queue import Queue, Empty
from base64 import b64encode, b64decode
from PySide6 import QtCore
from uuid import uuid4
from hashlib import sha3_512
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.hazmat.primitives.serialization import PublicFormat
from cryptography.hazmat.primitives.serialization import load_der_public_key
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.exceptions import InvalidTag

# Amount of data to place in each message
MESSAGE_DATA_SIZE = 8192 * 5

# Needs to be a bit bigger than MESSAGE_DATA_SIZE
RECV_SIZE = MESSAGE_DATA_SIZE + 1024

# All functions use this to run. Checks if the program is closing.
closeSoftwareLock = threading.Lock()
closeSoftware = False


# Has to be QObject for Signals to work.
class CommunicationsHandler(QtCore.QObject):
    """
    This class handles communication with a LinkScope server.

    Convention for variables changes here - all variables that have to do with network communications
      are in snake_case. This makes them easy to differentiate from others, if it is important to track
      what came from a network and what did not. This is also the case server-side.
    """

    connected_to_server_listener = QtCore.Signal(str)
    receive_question_answer = QtCore.Signal(dict)
    receive_chat_message = QtCore.Signal(str)
    receive_collectors_signal = QtCore.Signal(dict, dict)
    receive_start_collector_signal = QtCore.Signal(str, str, str, list, dict)
    receive_collector_result_signal = QtCore.Signal(str, str, str, list)
    receive_resolutions_signal = QtCore.Signal(dict)
    receive_completed_resolution_result_signal = QtCore.Signal(str, list, str)
    receive_completed_resolution_string_result_signal = QtCore.Signal(str, str, str)
    receive_document_summary_signal = QtCore.Signal(str, str)
    remove_server_resolution_from_running_signal = QtCore.Signal(str)
    receive_projects_list_signal = QtCore.Signal(list)
    delete_server_project_signal = QtCore.Signal(str)
    receive_project_canvases_list_signal = QtCore.Signal(list)
    open_project_signal = QtCore.Signal(str)
    close_project_signal = QtCore.Signal()
    open_project_canvas_signal = QtCore.Signal(str)
    close_project_canvas_signal = QtCore.Signal(str)
    receive_project_database_update = QtCore.Signal(dict, int)
    receive_project_canvas_update_node = QtCore.Signal(str, str)
    receive_project_canvas_update_link = QtCore.Signal(str, tuple)
    receive_sync_database = QtCore.Signal(dict, dict)
    status_message_signal = QtCore.Signal(str, bool)
    receive_project_file_list = QtCore.Signal(list)
    file_upload_finished_signal = QtCore.Signal(str)
    file_upload_abort_signal = QtCore.Signal(str)
    receive_sync_canvas_signal = QtCore.Signal(str, dict, dict)

    def __init__(self, mainWindow):

        super().__init__()

        self.inbox = Queue()

        self.mainWindow = mainWindow
        self.downloadingFiles = {}
        self.uploadingFiles = {}

        self.connected_to_server_listener.connect(self.mainWindow.connectedToServerListener)
        self.receive_question_answer.connect(self.mainWindow.questionAnswerListener)
        self.receive_chat_message.connect(self.mainWindow.receiveChatMessage)
        self.receive_collectors_signal.connect(self.mainWindow.addCollectorsFromServerListener)
        self.receive_start_collector_signal.connect(self.mainWindow.startNewCollectorListener)
        self.receive_collector_result_signal.connect(self.mainWindow.receiveCollectorResultListener)
        self.receive_resolutions_signal.connect(self.mainWindow.addResolutionsFromServerListener)
        self.receive_completed_resolution_result_signal.connect(self.mainWindow.resolutionSignalListener)
        self.receive_completed_resolution_string_result_signal.connect(self.mainWindow.resolutionSignalListener)
        self.receive_document_summary_signal.connect(self.mainWindow.receiveSummaryOfDocument)
        self.remove_server_resolution_from_running_signal.connect(self.mainWindow.cleanServerResolutionListener)
        self.delete_server_project_signal.connect(self.mainWindow.receiveProjectDeleteListener)
        self.receive_projects_list_signal.connect(self.mainWindow.receiveProjectsListListener)
        self.receive_project_canvases_list_signal.connect(self.mainWindow.receiveProjectCanvasesListListener)
        self.open_project_signal.connect(self.mainWindow.openServerProjectListener)
        self.open_project_canvas_signal.connect(self.mainWindow.openServerCanvasListener)
        self.close_project_signal.connect(self.mainWindow.closeServerProjectListener)
        self.close_project_canvas_signal.connect(self.mainWindow.closeServerCanvasListener)
        self.receive_project_database_update.connect(self.mainWindow.receiveServerDatabaseUpdate)
        self.receive_project_canvas_update_node.connect(self.mainWindow.receiveServerCanvasUpdate)
        self.receive_project_canvas_update_link.connect(self.mainWindow.receiveServerCanvasUpdate)
        self.receive_sync_database.connect(self.mainWindow.receiveSyncDatabaseListener)
        self.receive_project_file_list.connect(self.mainWindow.receiveFileListListener)
        self.file_upload_finished_signal.connect(self.mainWindow.fileUploadFinishedListener)
        self.file_upload_abort_signal.connect(self.mainWindow.receiveAbortUploadOfFiles)
        self.receive_sync_canvas_signal.connect(self.mainWindow.receiveSyncCanvasListener)
        self.status_message_signal.connect(self.mainWindow.statusMessageListener)

        self.cipher = None
        self.threadInc = None
        self.threadInb = None
        self.sock = None

    def beginCommunications(self, password: str, server: str, port: int = 3777) -> bool:
        global closeSoftwareLock
        global closeSoftware
        with closeSoftwareLock:  # Not strictly necessary, but might as well just in case.
            closeSoftware = False
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
            self.sock.connect((server, port))

            private_key = ec.generate_private_key(ec.SECP521R1())
            self.sock.send(private_key.public_key().public_bytes(
                Encoding.DER,
                format=PublicFormat.SubjectPublicKeyInfo))
            peer_public = load_der_public_key(self.sock.recv(RECV_SIZE))
            shared_key = private_key.exchange(ec.ECDH(), peer_public)
            derived_key = HKDF(
                algorithm=hashes.SHA3_256(),
                length=32,
                salt=None,
                info=b'Handshake'
            ).derive(shared_key)
            iv = sha3_512(derived_key).digest()[:16]
            self.cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
            encryptor = self.cipher.encryptor()
            decrypter = self.cipher.decryptor()

            passPad = 16 - (len(password) % 16)
            passMessage = encryptor.update(password.encode() + b"*" * passPad) + encryptor.finalize()
            self.sock.send(passMessage)
            messageReceived = decrypter.update(self.sock.recv(RECV_SIZE)) + decrypter.finalize()
            if messageReceived == b"Passphrase is OK":
                self.threadInc = threading.Thread(target=self.scanIncoming, daemon=True)
                self.threadInc.start()

                self.threadInb = threading.Thread(target=self.scanInbox, daemon=True)
                self.threadInb.start()

                return True
            elif messageReceived == b"Wrong Passphrase":
                raise ValueError('Incorrect Passphrase')

            self.mainWindow.MESSAGEHANDLER.warning("Server did not reply in the expected manner to "
                                                   "password authentication.", popUp=True)
        except ConnectionRefusedError:
            self.mainWindow.MESSAGEHANDLER.error("Did not connect: Server not running.", popUp=True, exc_info=False)
        except Exception as exception:
            self.mainWindow.MESSAGEHANDLER.error(f"Did not connect: {str(exception)}")

        try:
            if self.sock is not None:
                self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            # This would typically occur if the socket is already shut down.
            self.mainWindow.MESSAGEHANDLER.debug('Tried to shutdown socket that was already shut down.')
        try:
            self.sock.close()
        finally:
            self.sock = None

        return False

    def isConnected(self) -> bool:
        """
        Check if socket is in a working state.
        """
        return self.sock is not None and self.sock.fileno() != -1

    def close(self) -> None:
        global closeSoftwareLock
        global closeSoftware
        with closeSoftwareLock:
            closeSoftware = True
        self.closeSocket()
        for fileName in self.downloadingFiles:
            # Close open file handlers
            self.downloadingFiles[fileName].close()
            # saveDir = Path(fileName)
            saveDir = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")) / fileName
            if saveDir.exists():
                # Delete partly downloaded files.
                saveDir.unlink(missing_ok=True)
        self.downloadingFiles = {}
        self.uploadingFiles = {}

    def encryptTransmission(self, bytesObject) -> bytes:
        encryptor = self.cipher.encryptor()
        padNeeded = 16 - (len(bytesObject) % 16)
        message = encryptor.update(b'a' * padNeeded + bytesObject) + encryptor.finalize()
        return b64encode(message)

    def decryptTransmission(self, bytesObject) -> Union[bytes, None]:
        decrypter = self.cipher.decryptor()
        try:
            return decrypter.update(bytesObject) + decrypter.finalize()
        except InvalidTag:
            # If the ciphertext cannot be decrypted to a valid message, return None.
            return None

    def transmitMessage(self, messageJson: dict, showErrorOnBrokenPipe: bool = True) -> None:
        self.mainWindow.MESSAGEHANDLER.debug(f'Sending Message: {messageJson}')
        argEncoded = str(messageJson)
        largeMessageUUID = str(uuid4())
        try:
            for data in range(0, len(argEncoded), MESSAGE_DATA_SIZE):
                partArg = argEncoded[data:data + MESSAGE_DATA_SIZE]
                done = data + MESSAGE_DATA_SIZE >= len(argEncoded)
                messageJson = {"uuid": largeMessageUUID,
                               "message": partArg,
                               "done": done}
                self.sock.send(self.encryptTransmission(dumps(messageJson)) + b'\x03\x03\x03\x03\x03')
        except BrokenPipeError:
            if showErrorOnBrokenPipe:
                self.mainWindow.MESSAGEHANDLER.error("Disconnected from server!", popUp=True, exc_info=False)
                self.mainWindow.disconnectFromServer()

    def closeSocket(self) -> None:
        """
        Called by the close function in this class when communications with the server are to be ended.
        :return:
        """
        try:
            self.transmitMessage({"Operation": "Close Socket", "Arguments": {}}, showErrorOnBrokenPipe=False)
        except (OSError, AttributeError):
            # OSError thrown due to bad file descriptor, i.e. server is closed.
            # AttributeError thrown if no connection was established while the software was running
            pass
        finally:
            with contextlib.suppress(OSError):
                # OSError thrown if the socket is already closed.
                if self.sock is not None:
                    self.sock.shutdown(socket.SHUT_RDWR)
            try:
                self.sock.close()
            finally:
                self.sock = None

    def scanIncoming(self) -> None:
        """
        This function listens for incoming data, and puts it in the queue if
        it exists.
        """
        preInbox = {}
        oldData = b''
        while True:
            try:
                receivedInfo = self.sock.recv(RECV_SIZE)
                if receivedInfo == b'':
                    # Socket closed.
                    break
                receivedInfo = oldData + receivedInfo
                messages = receivedInfo.split(b'\x03\x03\x03\x03\x03\x03\x03\x03')
                # Last message is either blank (i.e. '') or incomplete data, so we ignore it.
                oldData = messages[-1]
                messages = messages[:-1]
                for message in messages:
                    if len(message) == 0:
                        continue
                    message = b64decode(message)
                    decryptedInfo = self.decryptTransmission(message)
                    if decryptedInfo is None:
                        self.mainWindow.MESSAGEHANDLER.warning("Invalid message received from server.")
                        continue
                    receivedMessage = loads(re.sub(b'^a*', b'', decryptedInfo, count=1))
                    messageID = receivedMessage.get("uuid")
                    if messageID in preInbox:
                        preInbox[messageID]["message"] += receivedMessage.get("message")
                    else:
                        preInbox[messageID] = receivedMessage
                    if receivedMessage.get("done"):
                        preInbox[messageID]["message"] = literal_eval(preInbox[messageID]["message"])
                        self.inbox.put(preInbox.pop(messageID).get("message"))

            except socket.error as socketError:
                self.mainWindow.MESSAGEHANDLER.error(f'Socket Error: {str(socketError)}')
                # If something happens, wait 2 seconds then try again.
                with closeSoftwareLock:
                    if closeSoftware:
                        break
                time.sleep(2)
            except ValueError:
                # E.g.: Unpack failed: incomplete input
                # In this case, we are being sent fragmented messages.
                # They will be reconstructed eventually, once all the pieces get here.
                continue

    def askServerForCollectors(self, continuing_collectors_dict: dict) -> None:
        message = {"Operation": "Get Server Collectors",
                   "Arguments": {
                       'continuing_collectors_dict': continuing_collectors_dict
                   }}
        self.transmitMessage(message)

    def receiveStartCollector(self, collector_category: str, collector_name: str, collector_uid: str,
                              collector_entities: list, collector_parameters: dict):
        self.receive_start_collector_signal.emit(collector_category, collector_name, collector_uid,
                                                 collector_entities, collector_parameters)

    def receiveCollectors(self, server_collectors: dict, continuing_collectors_info: dict) -> None:
        self.receive_collectors_signal.emit(server_collectors, continuing_collectors_info)

    def startServerCollector(self, collector_name: str, collector_entities: list, collector_parameters: dict,
                             continueTimestamp: int = 0) -> None:
        collector_entities_to_send = []
        for entity in collector_entities:
            with contextlib.suppress(KeyError):
                dereferenced_entity = dict(entity)
                collector_entities_to_send.append(dereferenced_entity)
                # Icon is not necessary for any collector as of now: 2022/4/3.
                # Cutting it out saves data.
                dereferenced_entity['Icon'] = ''
        message = {'Operation': 'Start Server Collector',
                   'Arguments': {
                       'collector_name': collector_name,
                       'collector_entities': collector_entities_to_send,
                       'collector_parameters': collector_parameters,
                       'continue_time': continueTimestamp
                   }}
        self.transmitMessage(message)

    def stopServerCollector(self, collector_uid: str) -> None:
        message = {"Operation": "Stop Server Collector",
                   "Arguments": {
                       'collector_uid': collector_uid
                   }}
        self.transmitMessage(message)

    def receiveCollectorResult(self, collector_name: str, collector_uid: str, timestamp: str, results: list) -> None:
        self.receive_collector_result_signal.emit(collector_name, collector_uid, timestamp, results)

    def askServerForResolutions(self) -> None:
        message = {"Operation": "Get Server Resolutions",
                   "Arguments": {}}
        self.transmitMessage(message)

    def receiveResolutions(self, server_resolutions) -> None:
        self.receive_resolutions_signal.emit(server_resolutions)

    def runRemoteResolution(self, resolution_name: str, resolution_entities: list, resolution_parameters: dict,
                            resolution_uid: str) -> None:
        resolution_entities_to_send = []
        for entity in resolution_entities:
            with contextlib.suppress(KeyError):
                dereferenced_entity = dict(entity)
                resolution_entities_to_send.append(dereferenced_entity)
                dereferenced_entity['Icon'] = dereferenced_entity['Icon'].toBase64().data()
        message = {'Operation': 'Run Resolution',
                   'Arguments': {
                       'resolution_name': resolution_name,
                       'resolution_entities': resolution_entities_to_send,
                       'resolution_parameters': resolution_parameters,
                       'resolution_uid': resolution_uid
                   }}
        self.transmitMessage(message)

    def receiveResolutionResult(self, resolution_name: str, resolution_result: Union[list, str],
                                resolution_uid: str) -> None:
        if isinstance(resolution_result, str):
            self.receive_completed_resolution_string_result_signal.emit(resolution_name, resolution_result,
                                                                        resolution_uid)
        else:
            for res_result in resolution_result:
                if res_icon := res_result[0].get('Icon'):
                    res_result[0]['Icon'] = QtCore.QByteArray(b64decode(res_icon))
            self.receive_completed_resolution_result_signal.emit(resolution_name, resolution_result,
                                                                 resolution_uid)
        self.remove_server_resolution_from_running_signal.emit(resolution_uid)

    def abortResolution(self, resolution_name: str, resolution_uid: str) -> None:
        message = {'Operation': 'Abort Resolution',
                   'Arguments': {
                       'resolution_name': resolution_name,
                       'resolution_uid': resolution_uid
                   }}
        self.transmitMessage(message)

    def askProjectsList(self) -> None:
        message = {'Operation': 'Get Projects List',
                   'Arguments': {}}
        self.transmitMessage(message)

    def receiveProjectsList(self, projects: list) -> None:
        self.receive_projects_list_signal.emit(projects)

    def createProject(self, projectName: str, projectPassword: str) -> None:
        if self.isConnected():
            message = {'Operation': 'Create Project',
                       'Arguments': {'project_name': projectName, 'password': projectPassword}}
            self.transmitMessage(message)

    def openProject(self, project_name: str, projectPassword: str) -> None:
        if self.isConnected():
            message = {'Operation': 'Open Project',
                       'Arguments': {'project_name': project_name, 'password': projectPassword}}
            self.transmitMessage(message)

    def closeProject(self, project_name: str) -> None:
        if self.isConnected():
            message = {'Operation': 'Close Project',
                       'Arguments': {'project_name': project_name}}
            self.transmitMessage(message)

    def askProjectCanvasesList(self, project_name: str) -> None:
        if self.isConnected():
            message = {'Operation': 'List Synced Canvases',
                       'Arguments': {'project_name': project_name}}
            self.transmitMessage(message)

    def receiveProjectCanvasesList(self, canvases: list) -> None:
        self.receive_project_canvases_list_signal.emit(canvases)

    def askQuestion(self, project_name: str, question: str, reader_value: int, retriever_value: int,
                    answer_count: int) -> None:
        if self.isConnected():
            message = {"Operation": "Ask Question",
                       "Arguments": {
                           'project_name': project_name,
                           'question': question[:256],
                           'reader_value': reader_value,
                           'retriever_value': retriever_value,
                           'answer_count': answer_count}}
            self.transmitMessage(message)

    def receiveQuestionAnswer(self, answer: list) -> None:
        self.receive_question_answer.emit(answer)

    def receiveTextMessage(self, chat_message: str) -> None:
        self.receive_chat_message.emit(chat_message)

    def sendTextMessage(self, project_name: str, chat_message: str) -> None:
        if self.isConnected():
            message = {"Operation": "Chat",
                       "Arguments": {
                           "project_name": project_name,
                           "chat_message": chat_message[:1024]}}  # Cap messages to prevent spam.
            self.transmitMessage(message)

    def syncDatabase(self, project_name: str, client_project_graph: nx.DiGraph) -> None:
        message = {'Operation': 'Sync Database',
                   'Arguments': {
                       'project_name': project_name,
                       'client_project_graph': str(self.mainWindow.RESOURCEHANDLER.deconstructGraph(
                           client_project_graph))
                   }}
        self.transmitMessage(message)

    def receiveSyncDatabase(self, database: str) -> None:
        database_nodes, database_edges = self.mainWindow.RESOURCEHANDLER.reconstructGraphFromString(database)
        self.receive_sync_database.emit(database_nodes, database_edges)

    def askServerForFileList(self, project_name: str) -> None:
        message = {"Operation": "Get File List",
                   "Arguments": {'project_name': project_name}}
        self.transmitMessage(message)

    def syncCanvasSend(self, project_name: str, canvas_name: str, canvas_graph: nx.DiGraph) -> None:
        if self.isConnected():
            message = {'Operation': "Sync Canvas",
                       'Arguments': {
                           'project_name': project_name,
                           'canvas_name': canvas_name,
                           "canvas_graph": str(self.mainWindow.RESOURCEHANDLER.deconstructGraph(canvas_graph))}}
            self.transmitMessage(message)

    def receiveSyncCanvas(self, canvas_name: str, canvas_graph: str) -> None:
        graph_nodes, graph_edges = self.mainWindow.RESOURCEHANDLER.reconstructGraphFromString(canvas_graph)
        self.receive_sync_canvas_signal.emit(canvas_name, graph_nodes, graph_edges)

    def closeCanvas(self, project_name: str, canvas_name: str) -> None:
        if self.isConnected():
            message = {'Operation': 'Close Canvas',
                       'Arguments': {'project_name': project_name,
                                     'canvas_name': canvas_name}}
            self.transmitMessage(message)

    # Items are sent both from the database and from the canvas.
    # Items are added to the database from the canvas, but items can be
    #   removed from the canvas without removing them from the database.
    # Furthermore, one might want to add items to the the database, but not
    #   to a particular canvas.
    # Being verbose is better than prematurely optimizing for a few kbps of
    #   network traffic.
    def receiveDatabaseUpdateEvent(self, entity_json: dict, add: int) -> None:
        with contextlib.suppress(KeyError):
            entity_json['Icon'] = QtCore.QByteArray(b64decode(entity_json['Icon']))
        self.receive_project_database_update.emit(entity_json, add)

    def sendDatabaseUpdateEvent(self, project_name: str, entity_json: dict, add: int) -> None:
        with contextlib.suppress(KeyError):
            entity_json['Icon'] = entity_json['Icon'].toBase64().data()
        message = {"Operation": "Update Project Entities",
                   "Arguments": {
                       'project_name': project_name,
                       "entity_json": entity_json,
                       "add": add}}
        self.transmitMessage(message)

    def receiveCanvasUpdateEvent(self, canvas_name: str, entity_or_link_uid: Union[str, tuple]) -> None:
        if isinstance(entity_or_link_uid, str):
            self.receive_project_canvas_update_node.emit(canvas_name, entity_or_link_uid)
        else:
            self.receive_project_canvas_update_link.emit(canvas_name, entity_or_link_uid)

    def sendCanvasUpdateEvent(self, project_name: str, canvas_name: str,
                              entity_or_link_uid: Union[str, tuple]) -> None:
        message = {"Operation": "Update Canvas Entities",
                   "Arguments": {
                       'project_name': project_name,
                       "canvas_name": canvas_name,
                       "entity_or_link_uid": entity_or_link_uid}}
        self.transmitMessage(message)

    def receiveFileList(self, file_list: list) -> None:
        self.receive_project_file_list.emit(file_list)

    def sendFile(self, project_name: str, file_name: str, filePath: Path) -> None:
        """
        Starts a thread, calling sendFileHelper to send the file specified.

        :param project_name:
        :param file_name:
        :param filePath:
        :return:
        """
        sendHelperThread = threading.Thread(target=self.sendFileHelper, daemon=True,
                                            args=(project_name, file_name, filePath))
        self.uploadingFiles[file_name] = sendHelperThread
        sendHelperThread.start()

    def sendFileHelper(self, project_name: str, file_name: str, filePath: Path) -> None:
        """
        Sends file in chunks to avoid loading the entire thing in memory.

        :param project_name:
        :param file_name:
        :param filePath:
        :return:
        """
        if not filePath.exists() or not filePath.is_file():
            return
        with open(filePath, 'rb') as fileHandler:
            currThread = threading.currentThread()
            while getattr(currThread, "continue_running", True):
                filePart = fileHandler.read(512)
                if not filePart:
                    messageJson = {"Operation": "File Upload Done",
                                   "Arguments": {
                                       'project_name': project_name,
                                       'file_name': file_name
                                   }}
                    self.transmitMessage(messageJson)
                    break
                messageJson = {"Operation": "File Upload",
                               "Arguments": {
                                   'project_name': project_name,
                                   'file_name': file_name,
                                   'file_contents': filePart
                               }}
                self.transmitMessage(messageJson)

    def sendFileAbort(self, project_name: str, file_name: str) -> None:
        with contextlib.suppress(KeyError):
            uploadToAbort = self.uploadingFiles.pop(file_name)
            uploadToAbort.continue_running = False
            messageJson = {"Operation": "File Upload Abort",
                           "Arguments": {
                               'project_name': project_name,
                               'file_name': file_name
                           }}
            self.transmitMessage(messageJson)

    def scanInbox(self) -> None:
        """
        This function checks if there is anything in the inbox, and if
        there is, calls the appropriate functions.
        """
        prevMesg = None
        while True:
            try:
                message = self.inbox.get(timeout=0.2)
            except Empty:
                with closeSoftwareLock:
                    if closeSoftware:
                        return
                    time.sleep(0.2)
                    continue
            if prevMesg == message:
                # Same message, do not waste time handling.
                continue
            self.mainWindow.MESSAGEHANDLER.debug(f'Message to handle: {str(message)}')
            operation = message['Operation']
            arguments = message['Arguments']
            if operation == 'Get Server Resolutions':
                self.receiveResolutions(**arguments)
            elif operation == 'Get Projects List':
                self.receiveProjectsList(**arguments)
            elif operation == 'Status Message':
                self.handleStatusMessage(**arguments)
            elif operation == 'List Synced Canvases':
                self.receiveProjectCanvasesList(**arguments)
            elif operation == 'Resolution Result':
                self.receiveResolutionResult(**arguments)
            elif operation == 'Collector Results Signal':
                self.receiveCollectorResult(**arguments)
            elif operation == "Chat":
                self.receiveTextMessage(**arguments)
            elif operation == "Sync Database":
                self.receiveSyncDatabase(**arguments)
            elif operation == "Sync Canvas":
                self.receiveSyncCanvas(**arguments)
            elif operation == "Answer Question":
                self.receiveQuestionAnswer(**arguments)
            elif operation == "Update Project Entities":
                self.receiveDatabaseUpdateEvent(**arguments)
            elif operation == "Update Canvas Entities":
                self.receiveCanvasUpdateEvent(**arguments)
            elif operation == "File List":
                self.receiveFileList(**arguments)
            elif operation == "File Download":
                self.receiveFileListener(**arguments)
            elif operation == "Get File Summary":
                self.receiveFileSummaryListener(**arguments)
            elif operation == "File Upload Abort":
                self.receiveFileUploadAbort(**arguments)
            elif operation == "Get Server Collectors":
                self.receiveCollectors(**arguments)
            elif operation == "Start Collector":
                self.receiveStartCollector(**arguments)
            else:
                self.mainWindow.MESSAGEHANDLER.warning(f'Unhandled message: {str(message)} On Operation: '
                                                       f'{str(operation)}')
            prevMesg = message

    def handleStatusMessage(self, operation: str, message: str, status_code: int) -> None:
        """
        Operations that are completely server-side, or do not conform to the query - response model,
        send status messages to inform the client of what is going on.

        Status codes follow the same pattern as the ones in HTTP:
        200 - Operation Successful.
        404 - A requested resource was not found
        403 - Access to the requested resource is forbidden
        500 - Server could not adequately handle the request.
        :param operation:
        :param message:
        :param status_code:
        :return:
        """
        if status_code == 200:
            if operation == 'Abort Resolution':
                # Remove resolution from resolutions list.
                resolution_uid = message.split(': ', 1)[1]
                self.remove_server_resolution_from_running_signal.emit(resolution_uid)
            elif operation == 'Close Canvas':
                canvas_name = message.split(': ', 1)[1]
                self.close_project_canvas_signal.emit(canvas_name)
            elif operation == 'Close Project':
                self.close_project_signal.emit()
            elif operation == 'Connect To Server':
                server_name = message.split(': ', 1)[1]
                self.connected_to_server_listener.emit(server_name)
            elif operation in {'Create Project', 'Create Canvas', 'Stop Collector'}:
                # No need to do anything for these.
                pass
            elif operation == 'Delete Project':
                # Remove project from server projects list.
                project_name = message.split(': ', 1)[1]
                self.delete_server_project_signal.emit(project_name)
            elif operation == 'File Download Done':
                file_name = message.split(': ', 1)[1]
                self.receiveFileDoneListener(file_name)
            elif operation == 'File Upload Abort':
                file_name = message.split(': ', 1)[1]
                # Remove file from uploading files list.
                self.file_upload_abort_signal.emit(file_name)
            elif operation == 'File Upload':
                file_name = message.split(': ', 1)[1]
                self.file_upload_finished_signal.emit(file_name)
            elif operation == 'Open Canvas':
                canvas_name = message.split(': ', 1)[1]
                self.open_project_canvas_signal.emit(canvas_name)
            elif operation == 'Open Project':
                projectName = message.split(': ', 1)[1]
                self.open_project_signal.emit(projectName)
            elif operation == 'Opening Project':
                self.status_message_signal.emit(message, True)
            else:
                self.mainWindow.MESSAGEHANDLER.warning(f'Unhandled status message: {message} Code: {status_code} '
                                                       f'On Operation: {operation}')

        elif status_code == 404 and message == 'No project with the specified name exists!':
            self.close_project_signal.emit()
        else:
            self.status_message_signal.emit(f'Operation {operation} failed with status code {status_code}: {message}',
                                            True)

    def receiveFile(self, project_name: str, file_name: str, saveDir: Path) -> None:
        # Do not download files already being downloaded.
        if self.downloadingFiles.get(file_name) is None:
            fileHandler = open(saveDir, "wb")
            self.downloadingFiles[file_name] = fileHandler

            message = {'Operation': 'File Download',
                       'Arguments': {
                           'project_name': project_name,
                           'file_name': file_name
                       }}
            self.transmitMessage(message)

    def receiveFileListener(self, file_name: str, file_contents: bytes) -> None:
        try:
            fileHandler = self.downloadingFiles.get(file_name)
            fileHandler.write(file_contents)
        except Exception:
            # In case something goes wrong in the middle of writing.
            self.mainWindow.MESSAGEHANDLER.warning(f'Received data for file: {file_name} but no valid file handler '
                                                   f'exists for this file.')

    def receiveFileDoneListener(self, file_name: str) -> None:
        fileHandler = self.downloadingFiles.pop(file_name)
        if fileHandler is None:
            self.mainWindow.MESSAGEHANDLER.warning(f'Received file: {file_name} but no file handler exists for this '
                                                   f'file.')

            return

        fileHandler.close()
        self.status_message_signal.emit(f'Finished downloading file from server: {file_name}', True)

    def receiveFileAbort(self, project_name: str, file_name: str) -> None:
        messageJson = {"Operation": "File Download Abort",
                       "Arguments": {
                           'project_name': project_name,
                           'file_name': file_name
                       }}
        self.transmitMessage(messageJson)
        fileHandler = self.downloadingFiles.pop(file_name)
        if fileHandler is None:
            return
        fileHandler.close()
        abortedPath = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")) / file_name
        abortedPath.unlink(missing_ok=True)

    def deleteProject(self, project_name: str) -> None:
        message = {"Operation": "Delete Project",
                   "Arguments": {
                       'project_name': project_name}}
        self.transmitMessage(message)

    def askServerForFileSummary(self, project_name: str, document_name: str) -> None:
        message = {"Operation": "Get File Summary",
                   "Arguments": {
                       'project_name': project_name,
                       'document_name': document_name}}
        self.transmitMessage(message)

    def receiveFileSummaryListener(self, document_name: str, summary: str) -> None:
        self.receive_document_summary_signal.emit(document_name, summary)

    def receiveFileUploadAbort(self, file_name: str) -> None:
        """
        If we are told by the server to stop uploading a file,
        we should do so (i.e. because no space left on server),
        to avoid wasting bandwidth.

        :param file_name:
        :return:
        """
        with contextlib.suppress(KeyError):
            uploadToAbort = self.uploadingFiles.pop(file_name)
            uploadToAbort.continue_running = False
            self.file_upload_abort_signal.emit(file_name)

    def sendFileAbortAll(self, project_name: str) -> None:
        """
        Abort the sending of all files currently being transmitted.

        :param project_name:
        :return:
        """
        for file_name in dict(self.uploadingFiles):
            with contextlib.suppress(KeyError):
                uploadToAbort = self.uploadingFiles.pop(file_name)
                uploadToAbort.continue_running = False
                messageJson = {"Operation": "File Upload Abort",
                               "Arguments": {
                                   'project_name': project_name,
                                   'file_name': file_name
                               }}
                self.transmitMessage(messageJson)

    def receiveFileAbortAll(self, project_name: str) -> None:
        """
        Abort the downloading of all files currently being transmitted.

        :param project_name:
        :return:
        """
        for file_name in dict(self.downloadingFiles):
            messageJson = {"Operation": "File Download Abort",
                           "Arguments": {
                               'project_name': project_name,
                               'file_name': file_name
                           }}
            self.transmitMessage(messageJson)
            fileHandler = self.downloadingFiles.pop(file_name)
            if fileHandler is None:
                return
            fileHandler.close()
            abortedPath = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")) / file_name
            abortedPath.unlink(missing_ok=True)
