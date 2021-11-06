#!/usr/bin/env python3

from typing import Union
from pathlib import Path
from msgpack import loads, dumps
import socket
import threading
import time
import pickle
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

# All functions use this to run. Checks if the program is closing.
closeSoftwareLock = threading.Lock()
closeSoftware = False


# Has to be QObject for Signals to work.
class CommunicationsHandler(QtCore.QObject):
    """
    This class handles communication with a Nexus server.

    Convention for variables changes here - all variables that have to do with network communications
      are in snake_case. This makes them easy to differentiate from others, if it is important to track
      what came from a network and what did not. This is also the case server-side.
    """

    connected_to_server_listener = QtCore.Signal(str)
    receive_question_answer = QtCore.Signal(dict)
    receive_chat_message = QtCore.Signal(str)
    receive_resolutions_signal = QtCore.Signal(dict)
    receive_completed_resolution_result_signal = QtCore.Signal(str, list)
    receive_completed_resolution_string_result_signal = QtCore.Signal(str, str)
    receive_document_summary_signal = QtCore.Signal(str, str)
    remove_server_resolution_from_running_signal = QtCore.Signal(str)
    receive_projects_list_signal = QtCore.Signal(list)
    receive_project_canvases_list_signal = QtCore.Signal(list)
    open_project_signal = QtCore.Signal(str)
    close_project_signal = QtCore.Signal()
    open_project_canvas_signal = QtCore.Signal(str)
    close_project_canvas_signal = QtCore.Signal(str)
    receive_project_database_update = QtCore.Signal(dict, bool)
    receive_project_canvas_update = QtCore.Signal(str, str)
    receive_sync_database = QtCore.Signal(nx.DiGraph)
    status_message_signal = QtCore.Signal(str, bool)
    receive_project_file_list = QtCore.Signal(list)
    file_upload_finished_signal = QtCore.Signal(str)
    file_upload_abort_signal = QtCore.Signal(str)
    receive_sync_canvas_signal = QtCore.Signal(str, nx.DiGraph)

    def __init__(self, mainWindow):

        super().__init__()

        self.inbox = Queue()

        self.mainWindow = mainWindow
        self.downloadingFiles = {}
        self.uploadingFiles = {}

        self.connected_to_server_listener.connect(self.mainWindow.connectedToServerListener)
        self.receive_question_answer.connect(self.mainWindow.questionAnswerListener)
        self.receive_chat_message.connect(self.mainWindow.receiveChatMessage)
        self.receive_resolutions_signal.connect(self.mainWindow.addResolutionsFromServerListener)
        self.receive_completed_resolution_result_signal.connect(self.mainWindow.resolutionSignalListener)
        self.receive_completed_resolution_string_result_signal.connect(self.mainWindow.resolutionSignalListener)
        self.receive_document_summary_signal.connect(self.mainWindow.receiveSummaryOfDocument)
        self.remove_server_resolution_from_running_signal.connect(self.mainWindow.cleanServerResolutionListener)
        self.receive_projects_list_signal.connect(self.mainWindow.receiveProjectsListListener)
        self.receive_project_canvases_list_signal.connect(self.mainWindow.receiveProjectCanvasesListListener)
        self.open_project_signal.connect(self.mainWindow.openServerProjectListener)
        self.open_project_canvas_signal.connect(self.mainWindow.openServerCanvasListener)
        self.close_project_signal.connect(self.mainWindow.closeCurrentServerProject)
        self.close_project_canvas_signal.connect(self.mainWindow.closeServerCanvasListener)
        self.receive_project_database_update.connect(self.mainWindow.receiveServerDatabaseUpdate)
        self.receive_project_canvas_update.connect(self.mainWindow.receiveServerCanvasUpdate)
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

    def beginCommunications(self, password: str, server: str, port: int = 3777):
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
            peer_public = load_der_public_key(self.sock.recv(5120))
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
            messageReceived = decrypter.update(self.sock.recv(5120)) + decrypter.finalize()
            if messageReceived == b"Passphrase is OK":
                self.threadInc = threading.Thread(target=self.scanIncoming)
                self.threadInc.setDaemon(True)
                self.threadInc.start()

                self.threadInb = threading.Thread(target=self.scanInbox)
                self.threadInb.setDaemon(True)
                self.threadInb.start()

                return True
            elif messageReceived == b"Wrong Passphrase":
                raise ValueError('Incorrect Passphrase')

            self.mainWindow.MESSAGEHANDLER.warning("Server did not reply in the expected manner to "
                                                   "password authentication.", popUp=True)
        except Exception as exception:
            self.mainWindow.MESSAGEHANDLER.error("Did not connect: " + str(exception))

        try:
            if self.sock is not None:
                self.sock.shutdown(socket.SHUT_RDWR)
                self.sock.close()
                self.sock = None
        except OSError:
            # This would typically occur if the socket is already closed.
            self.mainWindow.MESSAGEHANDLER.info('Tried to close socket that was already closed.')

        return False

    def isConnected(self):
        """
        Check if socket is in a working state.
        """
        if self.sock is not None and self.sock.fileno() != -1:
            return True
        return False

    def close(self):
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

    def encryptTransmission(self, bytesObject):
        encryptor = self.cipher.encryptor()
        # No need to check for overflows or negative pads - transmitMessage practically ensures that the data
        #   sent will always be less than or equal to 1280 bytes.
        padNeeded = 1280 - len(bytesObject)
        message = encryptor.update(b'a' * padNeeded + bytesObject) + encryptor.finalize()
        return message

    def decryptTransmission(self, bytesObject):
        decrypter = self.cipher.decryptor()
        try:
            message = decrypter.update(bytesObject) + decrypter.finalize()
            return message
        except InvalidTag:
            # If the ciphertext cannot be decrypted to a valid message, return None.
            return None

    def transmitMessage(self, messageJson: dict, showErrorOnBrokenPipe: bool = True):
        # Note that Base64 encoded data is about 4/3 times the size of the original.
        # 768 * 4/3 = 1024
        print('Sending message:', messageJson)
        argEncoded = b64encode(pickle.dumps(messageJson))
        largeMessageUUID = str(uuid4())
        try:
            for data in range(0, len(argEncoded), 768):
                partArg = argEncoded[data:data + 768]
                done = data + 768 >= len(argEncoded)
                messageJson = {"uuid": largeMessageUUID,
                               "message": partArg.decode(),
                               "done": done}
                self.sock.send(self.encryptTransmission(dumps(messageJson)))
        except BrokenPipeError:
            if showErrorOnBrokenPipe:
                self.mainWindow.MESSAGEHANDLER.error("Disconnected from server!", popUp=True, exc_info=False)
                self.mainWindow.disconnectFromServer()

    def closeSocket(self):
        """
        Called by the close function in this class when communications with the server are to be ended.
        :return:
        """
        try:
            self.transmitMessage({"Operation": "Close Socket", "Arguments": {}}, showErrorOnBrokenPipe=False)
        except OSError:
            # Typically this is due to bad file descriptor, i.e. server is closed.
            pass
        except AttributeError:
            # This happens if no connection was established while the software was running
            pass
        finally:
            try:
                if self.sock is not None:
                    self.sock.shutdown(socket.SHUT_RDWR)
                    self.sock.close()
                    self.sock = None
            except OSError:
                # This would typically occur if the socket is already closed.
                pass

    def scanIncoming(self):
        """
        This function listens for incoming data, and puts it in the queue if
        it exists.
        """
        preInbox = {}
        while True:
            try:
                receivedInfo = self.sock.recv(5120)
                if receivedInfo == b'':
                    # Socket closed.
                    break
                for message in range(0, len(receivedInfo), 1280):
                    decryptedInfo = self.decryptTransmission(receivedInfo[message:message + 1280])
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
                        preInbox[messageID]["message"] = pickle.loads(b64decode(preInbox[messageID]["message"]))
                        self.inbox.put(preInbox.pop(messageID).get("message"))

            except socket.error as socketError:
                self.mainWindow.MESSAGEHANDLER.error('Socket Error: ' + str(socketError))
                # If something happens, wait 2 seconds then try again.
                closeSoftwareLock.acquire()
                if not closeSoftware:
                    closeSoftwareLock.release()
                    time.sleep(2)
                else:
                    closeSoftwareLock.release()
                    break
            except ValueError:
                # E.g.: Unpack failed: incomplete input
                pass
            except pickle.UnpicklingError:
                # If something went wrong with one of the packets, ignore.
                # User can re-sync the database if needed.
                # This rarely occurs in normal operation.
                pass
            except ModuleNotFoundError:
                # Missing module to unpickle message.
                pass

    def askServerForResolutions(self):
        message = {"Operation": "Get Server Resolutions",
                   "Arguments": {}}
        self.transmitMessage(message)

    def receiveResolutions(self, server_resolutions):
        self.receive_resolutions_signal.emit(server_resolutions)

    def runRemoteResolution(self, resolution_name: str, resolution_entities: list, resolution_parameters: dict,
                            resolution_uid: str):
        message = {'Operation': 'Run Resolution',
                   'Arguments': {
                       'resolution_name': resolution_name,
                       'resolution_entities': resolution_entities,
                       'resolution_parameters': resolution_parameters,
                       'resolution_uid': resolution_uid
                   }}
        self.transmitMessage(message)

    def receiveResolutionResult(self, resolution_name: str, resolution_result: Union[list, str], resolution_uid: str):
        if isinstance(resolution_result, str):
            self.receive_completed_resolution_string_result_signal.emit(resolution_name, resolution_result)
        else:
            self.receive_completed_resolution_result_signal.emit(resolution_name, resolution_result)
        self.remove_server_resolution_from_running_signal.emit(resolution_uid)

    def abortResolution(self, resolution_name: str, resolution_uid: str):
        message = {'Operation': 'Abort Resolution',
                   'Arguments': {
                       'resolution_name': resolution_name,
                       'resolution_uid': resolution_uid
                   }}
        self.transmitMessage(message)

    def askProjectsList(self):
        message = {'Operation': 'Get Projects List',
                   'Arguments': {}}
        self.transmitMessage(message)

    def receiveProjectsList(self, projects: list):
        self.receive_projects_list_signal.emit(projects)

    def createProject(self, projectName: str, projectPassword: str):
        if self.isConnected():
            message = {'Operation': 'Create Project',
                       'Arguments': {'project_name': projectName, 'password': projectPassword}}
            self.transmitMessage(message)

    def openProject(self, project_name: str, projectPassword: str):
        if self.isConnected():
            message = {'Operation': 'Open Project',
                       'Arguments': {'project_name': project_name, 'password': projectPassword}}
            self.transmitMessage(message)

    def closeProject(self, project_name: str):
        if self.isConnected():
            message = {'Operation': 'Close Project',
                       'Arguments': {'project_name': project_name}}
            self.transmitMessage(message)

    def askProjectCanvasesList(self, project_name: str):
        if self.isConnected():
            message = {'Operation': 'List Synced Canvases',
                       'Arguments': {'project_name': project_name}}
            self.transmitMessage(message)

    def receiveProjectCanvasesList(self, canvases: list):
        self.receive_project_canvases_list_signal.emit(canvases)

    def askQuestion(self, project_name: str, question: str, reader_value: int, retriever_value: int, answer_count: int):
        if self.isConnected():
            message = {"Operation": "Ask Question",
                       "Arguments": {
                           'project_name': project_name,
                           'question': question[:256],
                           'reader_value': reader_value,
                           'retriever_value': retriever_value,
                           'answer_count': answer_count}}
            self.transmitMessage(message)

    def receiveQuestionAnswer(self, answer: list):
        self.receive_question_answer.emit(answer)

    def receiveTextMessage(self, chat_message: str):
        self.receive_chat_message.emit(chat_message)

    def sendTextMessage(self, project_name: str, chat_message: str):
        if self.isConnected():
            message = {"Operation": "Chat",
                       "Arguments": {
                           "project_name": project_name,
                           "chat_message": chat_message[:1024]}}
            self.transmitMessage(message)

    def syncDatabase(self, project_name: str, client_project_graph: nx.DiGraph):
        message = {'Operation': 'Sync Database',
                   'Arguments': {
                       'project_name': project_name,
                       'client_project_graph': client_project_graph
                   }}
        self.transmitMessage(message)

    def receiveSyncDatabase(self, database: nx.DiGraph):
        self.receive_sync_database.emit(database)

    def askServerForFileList(self, project_name: str):
        message = {"Operation": "Get File List",
                   "Arguments": {'project_name': project_name}}
        self.transmitMessage(message)

    def syncCanvasSend(self, project_name: str, canvas_name: str, canvas_graph: nx.DiGraph):
        if self.isConnected():
            message = {'Operation': "Sync Canvas",
                       'Arguments': {
                           'project_name': project_name,
                           'canvas_name': canvas_name,
                           "canvas_graph": canvas_graph}}
            self.transmitMessage(message)

    def receiveSyncCanvas(self, canvas_name: str, canvas_graph: nx.DiGraph):
        self.receive_sync_canvas_signal.emit(canvas_name, canvas_graph)

    def closeCanvas(self, project_name: str, canvas_name: str):
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
    def receiveDatabaseUpdateEvent(self, entity_json: dict, add: bool):
        self.receive_project_database_update.emit(entity_json, add)

    def sendDatabaseUpdateEvent(self, project_name: str, entity_json: dict, add: bool):
        message = {"Operation": "Update Project Entities",
                   "Arguments": {
                       'project_name': project_name,
                       "entity_json": entity_json,
                       "add": add}}
        self.transmitMessage(message)

    def receiveCanvasUpdateEvent(self, canvas_name: str, entity_or_link_uid: str):
        self.receive_project_canvas_update.emit(canvas_name, entity_or_link_uid)

    def sendCanvasUpdateEvent(self, project_name: str, canvas_name: str, entity_or_link_uid: Union[str, tuple]):
        message = {"Operation": "Update Canvas Entities",
                   "Arguments": {
                       'project_name': project_name,
                       "canvas_name": canvas_name,
                       "entity_or_link_uid": entity_or_link_uid}}
        self.transmitMessage(message)

    def receiveFileList(self, file_list: list):
        self.receive_project_file_list.emit(file_list)

    def sendFile(self, project_name: str, file_name: str, filePath: Path):
        """
        Starts a thread, calling sendFileHelper to send the file specified.

        :param project_name:
        :param file_name:
        :param filePath:
        :return:
        """
        sendHelperThread = threading.Thread(target=self.sendFileHelper, args=(project_name, file_name, filePath))
        sendHelperThread.setDaemon(True)
        self.uploadingFiles[file_name] = sendHelperThread
        sendHelperThread.start()

    def sendFileHelper(self, project_name: str, file_name: str, filePath: Path):
        """
        Sends file in chunks to avoid loading the entire thing in memory.

        :param project_name:
        :param file_name:
        :param filePath:
        :return:
        """
        if not filePath.exists() or not filePath.is_file():
            return
        fileHandler = open(filePath, 'rb')
        print('Sending file:', filePath)

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
        fileHandler.close()

    def sendFileAbort(self, project_name: str, file_name: str):
        try:
            uploadToAbort = self.uploadingFiles.pop(file_name)
            uploadToAbort.continue_running = False
            messageJson = {"Operation": "File Upload Abort",
                           "Arguments": {
                               'project_name': project_name,
                               'file_name': file_name
                           }}
            self.transmitMessage(messageJson)
        except KeyError:
            pass

    def scanInbox(self):
        """
        This function checks if there is anything in the inbox, and if
        there is, calls the appropriate functions.
        """
        while True:
            try:
                message = self.inbox.get(timeout=0.1)
            except Empty:
                with closeSoftwareLock:
                    if not closeSoftware:
                        time.sleep(0.1)
                        continue
                    else:
                        return
            print('Message To handle:', message)  # TODO Make this logging.
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
            elif operation == "Delete File":
                pass
            else:
                self.mainWindow.MESSAGEHANDLER.warning('Unhandled message: ' + str(message) +
                                                       ' On Operation: ' + str(operation))

    def handleStatusMessage(self, operation: str, message: str, status_code: int):
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
        if status_code != 200:
            self.status_message_signal.emit('Operation ' + operation + ' failed with status code ' +
                                            str(status_code) + ': ' + message, True)
        else:
            if operation == 'Create Project':
                # No need to do anything here. Creating a new project also opens it.
                pass
            elif operation == 'Open Project':
                projectName = message.split(': ', 1)[1]
                self.open_project_signal.emit(projectName)
            # Show the user that the server is doing something.
            elif operation == 'Opening Project':
                self.status_message_signal.emit(message, True)
            elif operation == 'Close Project':
                self.close_project_signal.emit()
            elif operation == 'Create Canvas':
                # No need to do anything here. Creating a new canvas also opens it.
                pass
            elif operation == 'Open Canvas':
                canvas_name = message.split(': ', 1)[1]
                self.open_project_canvas_signal.emit(canvas_name)
            elif operation == 'Close Canvas':
                canvas_name = message.split(': ', 1)[1]
                self.close_project_canvas_signal.emit(canvas_name)
            elif operation == 'Connect To Server':
                server_name = message.split(': ', 1)[1]
                self.connected_to_server_listener.emit(server_name)
            elif operation == 'File Upload':
                file_name = message.split(': ', 1)[1]
                self.file_upload_finished_signal.emit(file_name)
            elif operation == 'File Download Done':
                file_name = message.split(': ', 1)[1]
                self.receiveFileDoneListener(file_name)
            elif operation == 'Abort Resolution':
                # Remove resolution from resolutions list.
                resolution_uid = message.split(': ', 1)[1]
                self.remove_server_resolution_from_running_signal.emit(resolution_uid)
            elif operation == 'Delete File':
                # Remove file from uploaded files list.
                pass  # TODO
            elif operation == 'File Upload Abort':
                file_name = message.split(': ', 1)[1]
                # Remove file from uploading files list.
                self.file_upload_abort_signal.emit(file_name)
            else:
                self.mainWindow.MESSAGEHANDLER.warning('Unhandled status message: ' + message +
                                                       ' Code: ' + str(status_code) +
                                                       ' On Operation: ' + str(operation))

    def receiveFile(self, project_name: str, file_name: str):
        # Do not download files already being downloaded.
        if self.downloadingFiles.get(file_name) is None:
            saveDir = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")) / file_name
            fileHandler = open(saveDir, "wb")
            self.downloadingFiles[file_name] = fileHandler

            message = {'Operation': 'Download File',
                       'Arguments': {
                           'project_name': project_name,
                           'file_name': file_name
                       }}
            self.transmitMessage(message)

    def receiveFileListener(self, file_name: str, file_contents: bytes):
        try:
            fileHandler = self.downloadingFiles.get(file_name)
            fileHandler.write(file_contents)
        except Exception:
            # In case the file is deleted in the middle of writing, or anything else going wrong.
            self.mainWindow.MESSAGEHANDLER.warning('Received data for file: ' + file_name +
                                                   ' but no valid file handler exists for this file.')

    def receiveFileDoneListener(self, file_name: str):
        fileHandler = self.downloadingFiles.pop(file_name)
        if fileHandler is None:
            self.mainWindow.MESSAGEHANDLER.warning('Received file: ' + file_name +
                                                   ' but no file handler exists for this file.')
            return

        fileHandler.close()
        self.status_message_signal.emit('Finished downloading file from server: ' + file_name, False)

    def receiveFileAbort(self, project_name: str, file_name: str):
        messageJson = {"Operation": "Download File Abort",
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

    def deleteFile(self, project_name: str, file_name: str):
        message = {"Operation": "Delete File",
                   "Arguments": {
                       'project_name': project_name,
                       'file_name': file_name}}
        self.transmitMessage(message)

    def askServerForFileSummary(self, project_name: str, document_name: str):
        message = {"Operation": "Get File Summary",
                   "Arguments": {
                       'project_name': project_name,
                       'document_name': document_name}}
        self.transmitMessage(message)

    def receiveFileSummaryListener(self, document_name: str, summary: str):
        self.receive_document_summary_signal.emit(document_name, summary)

    def receiveFileUploadAbort(self, file_name: str):
        """
        If we are told by the server to stop uploading a file,
        we should do so (i.e. because no space left on server),
        to avoid wasting bandwidth.

        :param file_name:
        :return:
        """
        try:
            uploadToAbort = self.uploadingFiles.pop(file_name)
            uploadToAbort.continue_running = False
            self.file_upload_abort_signal.emit(file_name)
        except KeyError:
            pass

    def sendFileAbortAll(self, project_name: str):
        """
        Abort the sending of all files currently being transmitted.

        :param project_name:
        :return:
        """
        for file_name in self.uploadingFiles:
            try:
                uploadToAbort = self.uploadingFiles.pop(file_name)
                uploadToAbort.continue_running = False
                messageJson = {"Operation": "File Upload Abort",
                               "Arguments": {
                                   'project_name': project_name,
                                   'file_name': file_name
                               }}
                self.transmitMessage(messageJson)
            except KeyError:
                pass

    def receiveFileAbortAll(self, project_name: str):
        """
        Abort the downloading of all files currently being transmitted.

        :param project_name:
        :return:
        """
        for file_name in self.downloadingFiles:
            messageJson = {"Operation": "Download File Abort",
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
