#!/usr/bin/env python3

from shutil import move
from msgpack import load, dump
from threading import Lock
from pathlib import Path
from typing import Union

import networkx as nx


class EntitiesDB:
    """
    This is a class that handles the addition and removal of entities and
    links on a project-wide scale.
    """

    def __init__(self, mainWindow, messageHandler, resourceHandler) -> None:
        self.messageHandler = messageHandler
        self.resourceHandler = resourceHandler
        self.mainWindow = mainWindow
        self.dbLock = Lock()
        self.database = None

        self.loadDatabase()
        self.resetTimeline()

    def loadDatabase(self) -> None:
        """
        Load DiGraph from LinkScope Database file - msgpack dumped object.
        """
        with self.dbLock:
            if self.database is not None:
                self.save()
            databaseFile = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")).joinpath("LocalEntitiesDB.lsdb")
            self.messageHandler.debug(f'Opening Database at: {str(databaseFile)}')
            try:
                with open(databaseFile, "rb") as dbFile:
                    self.database = self.mainWindow.RESOURCEHANDLER.reconstructGraphFullFromFile(load(dbFile))
                self.messageHandler.info('Loaded Local Entities Database.')
            except FileNotFoundError:
                self.messageHandler.info('Creating new Local Entities Database.')
                self.database = nx.DiGraph()
            except Exception as exc:
                self.messageHandler.error(f'Cannot parse Database: {str(exc)}\nCreating new Local Entities Database.',
                                          popUp=True)
                self.database = nx.DiGraph()

    def resetTimeline(self) -> None:
        """
        Reset the timeline on dockBarThree to reflect the current state of the database.
        """
        with self.dbLock:
            if self.database is not None:
                self.mainWindow.resetTimeline(self.database)

    def updateTimeline(self, node, added: bool, updateGraph: bool = True) -> None:
        """
        Update the timeline on dockBarThree to reflect the newest change of the database.
        """
        with self.dbLock:
            self.mainWindow.updateTimeline(node, added, updateGraph)

    def save(self) -> None:
        """
        Saves the graph to the specified file.
        """

        # Get the database file path again, in case it changed.
        databaseFile = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")).joinpath("LocalEntitiesDB.lsdb")
        if databaseFile is None:
            raise ValueError('Database File is None, cannot save database.')
        with self.dbLock:
            tmpSavePath = databaseFile.with_suffix(f'{databaseFile.suffix}.tmp')
            with open(tmpSavePath, "wb") as dbFile:
                dump(self.mainWindow.RESOURCEHANDLER.deconstructGraphForFileDump(self.database), dbFile)
            move(tmpSavePath, databaseFile)
            self.messageHandler.info('Database Saved.')

    def addEntity(self, entJson: dict, fromServer: bool = False, updateTimeline: bool = True) -> Union[dict, None]:
        """
        Adds the entity represented by the json dictionary to the database.
        """
        with self.dbLock:
            returnValue = None

            # Check if we're overwriting an existing entity
            exists = None
            if entJson.get('uid') is not None:
                exists = self.getEntityNoLock(entJson.get('uid'))

            entity = self.resourceHandler.getEntityJson(
                entJson.get('Entity Type'),
                entJson)

            if entity is None:
                return returnValue
            # Use uid as key. Code is holdover from the time when primary field == uid.
            self.database.add_node(entity['uid'], **entity)
            returnValue = entity
            if exists:
                # Update canvases if the node already exists.
                self.mainWindow.updateEntityNodeLabelsOnCanvases(entity['uid'], entity[list(entity)[1]])

        if not fromServer:
            self.mainWindow.sendLocalDatabaseUpdateToServer(entity, 1)
        self.mainWindow.populateEntitiesWidget(returnValue, add=True)

        if updateTimeline:
            if exists is not None:
                # Remove existing item before re-adding.
                self.updateTimeline(exists, False, updateGraph=False)
            self.updateTimeline(entity, True, updateGraph=True)

        return returnValue

    def addEntities(self, entitiesJsonList: Union[list, set, tuple], fromServer: bool = False) -> list:
        with self.dbLock:
            returnValue = []

            for entJson in entitiesJsonList:
                # Check if we're overwriting an existing entity
                exists = None
                if entJson.get('uid') is not None:
                    exists = self.getEntityNoLock(entJson.get('uid'))

                entity = self.resourceHandler.getEntityJson(
                    entJson.get('Entity Type'),
                    entJson)

                if entity is None:
                    continue
                # Use uid as key. Code is holdover from the time when primary field == uid.
                self.database.add_node(entity['uid'], **entity)
                returnValue.append(entity)
                if exists:
                    # Update canvases if the node already exists.
                    self.mainWindow.updateEntityNodeLabelsOnCanvases(entity['uid'], entity[list(entity)[1]])
                if not fromServer:
                    self.mainWindow.sendLocalDatabaseUpdateToServer(entity, 1)
                self.mainWindow.populateEntitiesWidget(entity, add=True)

        self.resetTimeline()

        return returnValue

    def addLink(self, linkJson: dict, fromServer: bool = False, overwrite: bool = False) -> Union[dict, None]:
        """
        Add a link between two entities in the database.

        :param overwrite:
        :param linkJson:
        :param fromServer:
        :return:
        """
        with self.dbLock:
            exists = self.isLinkNoLock(linkJson['uid'])
            link = self.resourceHandler.getLinkJson(linkJson)
            if link is None:
                # This can technically be caused by a race condition if the user
                #   either tries really hard or gets really unlucky.
                # Caused by deleting a node faster than the link can be created.
                self.messageHandler.error("Attempted to add Link with "
                                          "no uid to database.", popUp=True)
                return None
            else:
                linkUID = link['uid']
                if exists:
                    newRes = link.get('Resolution')
                    newNotes = link.get('Notes')
                    if newRes and newRes != exists['Resolution']:
                        if overwrite:
                            link['Resolution'] = newRes
                        else:
                            link['Resolution'] = f"{exists['Resolution']} | {newRes}"
                    if newNotes and newNotes != exists['Notes'] and newNotes != 'None':
                        if overwrite:
                            link['Notes'] = str(newNotes)
                        else:
                            link['Notes'] = f"{exists['Notes']}\n\n{str(newNotes)}"
                    exists.update(link)
                    link.update(exists)
                    # Update canvases if the link already exists.
                    # We can do this before updating the database here because the GUI will be updated only after this
                    #   function returns. If we ever execute this function outside the main event loop, we will need
                    #   to alter the execution flow.
                    self.mainWindow.updateLinkLabelsOnCanvases(f"{linkUID[0]}{linkUID[1]}", link['Resolution'])
                self.database.add_edge(linkUID[0], linkUID[1], **link)

        if not fromServer:
            if overwrite:
                self.mainWindow.sendLocalDatabaseUpdateToServer(link, 3)
            else:
                self.mainWindow.sendLocalDatabaseUpdateToServer(link, 1)
        return link

    def getEntity(self, uid: str) -> Union[dict, None]:
        """
        Returns the attributes of the given entity uid as a dict.
        """
        with self.dbLock:
            returnValue = None
            try:
                returnValue = self.database.nodes[uid]
            except KeyError:
                self.messageHandler.warning(f"Tried to get entity with nonexistent UID: {uid}")
            finally:
                return returnValue

    def getAllEntities(self) -> Union[None, list]:
        """
        Returns a list containing the Json representation of every entity in the database.
        """
        with self.dbLock:
            returnValue = None
            try:
                returnValue = [self.database.nodes[node] for node in self.database.nodes()]
            except KeyError:
                self.messageHandler.error("Tried to get entity with nonexistent UID.")
            finally:
                return returnValue

    def getAllLinks(self) -> Union[None, list]:
        """
        Returns a list containing the Json representation of every link in the database.
        :return:
        """
        with self.dbLock:
            returnValue = None
            try:
                returnValue = [self.database.edges[edge] for edge in self.database.edges()]
            except KeyError:
                self.messageHandler.error("Tried to get link with nonexistent UID.")
            finally:
                return returnValue

    def getEntityNoLock(self, uid: str) -> Union[None, dict]:
        """
        Returns the attributes of the given entity uid as a dict.

        Does not lock, specifically meant for use by other functions in this
        class.
        """
        returnValue = None
        try:
            returnValue = self.database.nodes[uid]
        except KeyError:
            pass
        finally:
            return returnValue

    def getLink(self, uid) -> Union[None, dict]:
        """
        Returns the attributes of the given link uid as a dict.
        """
        with self.dbLock:
            returnValue = None
            try:
                returnValue = self.database.edges[uid]
            except KeyError:
                self.messageHandler.error(
                    "Tried to get link with nonexistent UID.")
            finally:
                return returnValue

    def removeEntity(self, uid: str, fromServer=False, updateTimeLine=True) -> None:
        """
        Removes the entity with the given uid, if it exists.
        """
        with self.dbLock:
            ent = None
            if self.isNodeNoLock(uid):
                ent = self.getEntityNoLock(uid)
                self.mainWindow.populateEntitiesWidget(ent, add=False)
                self.database.remove_node(uid)

        if ent is not None:
            self.mainWindow.handleGroupNodeUpdateAfterEntityDeletion(uid)  # Blocking - locks the db.
            if not fromServer:
                self.mainWindow.sendLocalDatabaseUpdateToServer(ent, 2)
            if updateTimeLine:
                self.updateTimeline(ent, False)

    def removeLink(self, uid, fromServer=False) -> None:
        """
        Removes the link with the given uid (in string or tuple form),
        if it exists.
        """
        with self.dbLock:
            if self.isLinkNoLock(uid):
                self.database.remove_edge(uid[0], uid[1])
        if not fromServer:
            self.mainWindow.sendLocalDatabaseUpdateToServer({"uid": uid}, 2)

    def doesEntityExist(self, primaryAttr: str) -> bool:
        """
        Checks if an entity with the specified primary attribute exists.
        """
        with self.dbLock:
            result = False
            for node in self.database.nodes():
                details = self.database.nodes[node]
                if details[list(details)[1]] == primaryAttr:
                    result = True
                    break
        return result

    def getEntityOfType(self, primaryAttr: str, entityType: str) -> Union[dict, None]:
        """
        Checks if an entity with the specified primary attribute exists, and if it does, return it.
        """
        result = None
        primaryField = self.resourceHandler.getPrimaryFieldForEntityType(entityType)
        if primaryField is None:
            return result
        with self.dbLock:
            for node in self.database.nodes():
                details = self.database.nodes[node]
                if details['Entity Type'] == entityType and details[primaryField] == primaryAttr:
                    result = dict(details)
                    break
        return result

    def getLinkIfExists(self, uid) -> Union[None, dict]:
        """
        Returns the attributes of the given link uid as a dict.
        Does not create an error if the link does not exist.
        """
        with self.dbLock:
            returnValue = None
            try:
                returnValue = self.database.edges[uid]
            except KeyError:
                pass
            finally:
                return returnValue

    def getIncomingLinks(self, uid: str):
        """
        Get all incoming edges for the given entity uid (primary attribute).
        """
        with self.dbLock:
            returnValue = self.database.in_edges(uid) if self.isNodeNoLock(uid) else None
        return returnValue

    def getOutgoingLinks(self, uid: str):
        """
        Get all outgoing edges for the given entity uid (primary attribute).
        """
        with self.dbLock:
            returnValue = self.database.out_edges(uid) if self.isNodeNoLock(uid) else None
        return returnValue

    def isNode(self, uid: Union[str, list, tuple]) -> bool:
        """
        Returns True if the uid (primary attribute) given exists as
        an entity, and False otherwise.
        """
        with self.dbLock:
            returnValue = isinstance(uid, str) and self.database.nodes.get(uid) is not None
        return returnValue

    def isNodeNoLock(self, uid: str) -> bool:
        """
        Returns True if the uid (primary attribute) given exists as
        an entity, and False otherwise.

        Used only in this class, as it does not lock.
        """
        return self.database.nodes.get(uid) is not None

    def isLink(self, uid: Union[str, list, tuple]) -> bool:
        """
        Returns True if the uid given exists as a link, and False otherwise.
        """
        with self.dbLock:
            returnValue = isinstance(uid, tuple) and self.database.edges.get(uid) is not None
        return returnValue

    def isLinkNoLock(self, uid: tuple) -> Union[bool, dict]:
        """
        Returns True if the uid given exists as a link, and False otherwise.
        
        Used only in this class, as it does not lock.
        """
        if self.database.edges.get(uid) is not None:
            return self.database.edges[uid]
        return False

    def getEntityType(self, uid: str) -> Union[None, dict]:
        with self.dbLock:
            returnValue = None
            try:
                returnValue = self.getEntityNoLock(uid)['Entity Type']
            except KeyError:
                pass
            finally:
                return returnValue

    def mergeDatabases(self, newDB_nodes: dict, newDB_edges: dict, fromServer=True) -> None:
        """
        Merges the existing database with the one provided.
        Overwrites older attributes with newer ones based on date last edited.
        """
        with self.dbLock:
            differenceGraph = nx.DiGraph()
            differenceGraph.add_nodes_from([(n, nDict)
                                            for n, nDict in newDB_nodes.items() if (n not in self.database.nodes()) or
                                            (
                                                    nDict.get('Date Last Edited', '') >
                                                    self.database.nodes[n].get('Date Last Edited', '')
                                            )
                                            ])
            differenceGraph.add_edges_from([(e[0], e[1], eDict)
                                            for e, eDict in newDB_edges.items() if (e not in self.database.edges()) or
                                            (
                                                    eDict.get('Date Last Edited', '') >
                                                    self.database.edges[e].get('Date Last Edited', '')
                                            )
                                            ])
            if differenceGraph.number_of_nodes():
                self.database = nx.compose(self.database, differenceGraph)
                # Some nodes given by differenceGraph may be empty dicts, with an existing node's uid as the key.
                for node in differenceGraph.nodes:
                    self.mainWindow.populateEntitiesWidget(self.database.nodes[node], add=True)

                if not fromServer and self.mainWindow.FCOM.isConnected():
                    # Assume we are already synced with server, so just send the difference.
                    self.mainWindow.FCOM.syncDatabase(self.mainWindow.SETTINGS.value("Project/Server/Project"),
                                                      differenceGraph)
