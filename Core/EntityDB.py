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

    def __init__(self, mainWindow, messageHandler, resourceHandler):
        self.messageHandler = messageHandler
        self.resourceHandler = resourceHandler
        self.mainWindow = mainWindow
        self.dbLock = Lock()
        self.database = None

        self.loadDatabase()
        self.resetTimeline()

    def loadDatabase(self):
        """
        Load DiGraph from LinkScope Database file - msgpack dumped object.
        """
        self.dbLock.acquire()
        if self.database is not None:
            self.save()
        databaseFile = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")).joinpath("LocalEntitiesDB.lsdb")
        self.messageHandler.debug('Opening Database at: ' + str(databaseFile))
        try:
            dbFile = open(databaseFile, "rb")
            self.database = self.mainWindow.RESOURCEHANDLER.reconstructGraphFullFromFile(load(dbFile))
            dbFile.close()
            self.messageHandler.info('Loaded Local Entities Database.')
        except FileNotFoundError:
            self.messageHandler.info('Creating new Local Entities Database.')
            self.database = nx.DiGraph()
        except Exception as exc:
            self.messageHandler.error('Cannot parse Database: ' + str(exc) + "\nCreating new Local Entities Database.",
                                      popUp=True)
            self.database = nx.DiGraph()
        finally:
            self.dbLock.release()

    def resetTimeline(self):
        """
        Reset the timeline on dockBarThree to reflect the current state of the entities database.
        """
        self.dbLock.acquire()
        if self.database is not None:
            self.mainWindow.resetTimeline(self.database)
        self.dbLock.release()

    def updateTimeline(self, node, added: bool, updateGraph: bool = True):
        """
        Update the timeline on dockBarThree to reflect the newest change of the entities database.
        """
        self.dbLock.acquire()
        self.mainWindow.updateTimeline(node, added, updateGraph)
        self.dbLock.release()

    def save(self):
        """
        Saves the graph to the specified file.
        """

        # Get the database file path again, in case it changed.
        databaseFile = Path(self.mainWindow.SETTINGS.value("Project/FilesDir")).joinpath("LocalEntitiesDB.lsdb")
        if databaseFile is None:
            raise ValueError('Database File is None, cannot save database.')
        self.dbLock.acquire()
        tmpSavePath = databaseFile.with_suffix(databaseFile.suffix + '.tmp')
        dbFile = open(tmpSavePath, "wb")
        dump(self.mainWindow.RESOURCEHANDLER.deconstructGraphForFileDump(self.database), dbFile)
        dbFile.close()
        move(tmpSavePath, databaseFile)
        self.messageHandler.info('Database Saved.')
        self.dbLock.release()

    def addEntity(self, entJson: dict, fromServer: bool = False, updateTimeline: bool = True):
        """
        Adds the entity represented by the json dictionary to the database.
        :param updateTimeline:
        :param entJson:
        :param fromServer:
        :return:
        """
        self.dbLock.acquire()
        returnValue = None

        # Check if we're overwriting an existing entity
        exists = None
        if entJson.get('uid') is not None:
            exists = self.getEntityNoLock(entJson.get('uid'))

        entity = self.resourceHandler.getEntityJson(
            entJson.get('Entity Type'),
            entJson)

        if entity is None:
            self.dbLock.release()
            return returnValue
        # Use uid as key. Code is holdover from time where primary field == uid.
        self.database.add_node(entity['uid'], **entity)
        returnValue = entity
        if exists:
            # Update canvases if the node already exists.
            self.mainWindow.updateEntityNodeLabelsOnCanvases(entity['uid'], entity[list(entity)[1]])
        self.dbLock.release()
        if not fromServer:
            self.mainWindow.sendLocalDatabaseUpdateToServer(entity, 1)
        self.mainWindow.populateEntitiesWidget(returnValue, add=True)

        if updateTimeline:
            if exists is not None:
                # Remove existing item before re-adding.
                self.updateTimeline(exists, False, updateGraph=False)
            self.updateTimeline(entity, True, updateGraph=True)

        return returnValue

    def addEntities(self, entsJsonList: Union[list, set, tuple], fromServer: bool = False):
        self.dbLock.acquire()
        returnValue = []

        for entJson in entsJsonList:
            # Check if we're overwriting an existing entity
            exists = None
            if entJson.get('uid') is not None:
                exists = self.getEntityNoLock(entJson.get('uid'))

            entity = self.resourceHandler.getEntityJson(
                entJson.get('Entity Type'),
                entJson)

            if entity is None:
                continue
            # Use uid as key. Code is holdover from time where primary field == uid.
            self.database.add_node(entity['uid'], **entity)
            returnValue.append(entity)
            if exists:
                # Update canvases if the node already exists.
                self.mainWindow.updateEntityNodeLabelsOnCanvases(entity['uid'], entity[list(entity)[1]])
            if not fromServer:
                self.mainWindow.sendLocalDatabaseUpdateToServer(entity, 1)
            self.mainWindow.populateEntitiesWidget(entity, add=True)

        self.dbLock.release()
        self.resetTimeline()

        return returnValue

    def addLink(self, linkJson: dict, fromServer: bool = False, overwrite: bool = False):
        """
        Add a link between two entities in the database.

        :param overwrite:
        :param linkJson:
        :param fromServer:
        :return:
        """
        self.dbLock.acquire()
        exists = self.isLinkNoLock(linkJson['uid'])
        link = self.resourceHandler.getLinkJson(linkJson)
        if link is None:
            # This can technically be caused by a race condition if the user
            #   either tries really hard or gets really unlucky.
            # Caused by deleting a node faster than the link can be created.
            self.messageHandler.error("Attempted to add Link with "
                                      "no uid to database.")
        else:
            linkUID = link['uid']
            if exists:
                newRes = link.get('Resolution')
                newNotes = link.get('Notes')
                if newRes and newRes != exists['Resolution']:
                    if overwrite:
                        link['Resolution'] = newRes
                    else:
                        link['Resolution'] = exists['Resolution'] + ' | ' + newRes
                if newNotes and newNotes != exists['Notes'] and newNotes != 'None':
                    if overwrite:
                        link['Notes'] = str(newNotes)
                    else:
                        link['Notes'] = exists['Notes'] + '\n\n' + str(newNotes)
                exists.update(link)
                link.update(exists)
                # Update canvases if the link already exists.
                # We can do this before updating the database here because the GUI will be updated only after this
                #   function returns. If we ever execute this function outside the main event loop, we will need
                #   to alter the execution flow.
                self.mainWindow.updateLinkLabelsOnCanvases(linkUID[0] + linkUID[1], link['Resolution'])
            self.database.add_edge(linkUID[0], linkUID[1], **link)

        self.dbLock.release()
        if not fromServer:
            if overwrite:
                self.mainWindow.sendLocalDatabaseUpdateToServer(link, 3)
            else:
                self.mainWindow.sendLocalDatabaseUpdateToServer(link, 1)
        return link

    def getEntity(self, uid: str):
        """
        Returns the attributes of the given entity uid as a dict.
        """
        self.dbLock.acquire()
        returnValue = None
        try:
            returnValue = self.database.nodes[uid]
        except KeyError:
            self.messageHandler.warning(
                "Tried to get entity with nonexistent UID: " + uid)
        finally:
            self.dbLock.release()
            return returnValue

    def getAllEntities(self):
        """
        Returns a list containing the Json representation of every entity in the database.
        """
        self.dbLock.acquire()
        returnValue = None
        try:
            returnValue = []
            for node in self.database.nodes():
                returnValue += [self.database.nodes[node]]
        except KeyError:
            self.messageHandler.error(
                "Tried to get entity with nonexistent UID.")
        finally:
            self.dbLock.release()
            return returnValue

    def getAllLinks(self):
        """
        Returns a list containing the Json representation of every link in the database.
        :return:
        """
        self.dbLock.acquire()
        returnValue = None
        try:
            returnValue = []
            for edge in self.database.edges():
                returnValue += [self.database.edges[edge]]
        except KeyError:
            self.messageHandler.error(
                "Tried to get link with nonexistent UID.")
        finally:
            self.dbLock.release()
            return returnValue

    def getEntityNoLock(self, uid: str):
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

    def getLink(self, uid):
        """
        Returns the attributes of the given link uid as a dict.
        """
        self.dbLock.acquire()
        returnValue = None
        try:
            returnValue = self.database.edges[uid]
        except KeyError:
            self.messageHandler.error(
                "Tried to get link with nonexistent UID.")
        finally:
            self.dbLock.release()
            return returnValue

    def removeEntity(self, uid: str, fromServer=False, updateTimeLine=True):
        """
        Removes the entity with the given uid, if it exists.
        """
        self.dbLock.acquire()
        ent = None
        if self.isNodeNoLock(uid):
            ent = self.getEntityNoLock(uid)
            self.mainWindow.populateEntitiesWidget(ent, add=False)
            self.database.remove_node(uid)
        self.dbLock.release()
        if ent is not None:
            self.mainWindow.handleGroupNodeUpdateAfterEntityDeletion(uid)  # Blocking - locks the db.
            if not fromServer:
                self.mainWindow.sendLocalDatabaseUpdateToServer(ent, 2)
            if updateTimeLine:
                self.updateTimeline(ent, False)

    def removeLink(self, uid, fromServer=False):
        """
        Removes the link with the given uid (in string or tuple form),
        if it exists.
        """
        self.dbLock.acquire()
        if self.isLinkNoLock(uid):
            self.database.remove_edge(uid[0], uid[1])
        self.dbLock.release()
        if not fromServer:
            self.mainWindow.sendLocalDatabaseUpdateToServer({"uid": uid}, 2)

    def doesEntityExist(self, primaryAttr: str):
        """
        Checks if an entity with the specified primary attribute exists.
        """
        self.dbLock.acquire()
        result = False
        for node in self.database.nodes():
            details = self.database.nodes[node]
            if details[list(details)[1]] == primaryAttr:
                result = True
                break
        self.dbLock.release()
        return result

    def getEntityOfType(self, primaryAttr: str, entityType: str):
        """
        Checks if an entity with the specified primary attribute exists, and if it does, return it.
        """
        result = None
        primaryField = self.resourceHandler.getPrimaryFieldForEntityType(entityType)
        if primaryField is None:
            return result
        self.dbLock.acquire()
        for node in self.database.nodes():
            details = self.database.nodes[node]
            if details['Entity Type'] == entityType and details[primaryField] == primaryAttr:
                result = dict(details)
                break
        self.dbLock.release()
        return result

    def getLinkIfExists(self, uid):
        """
        Returns the attributes of the given link uid as a dict.
        Does not create an error if the link does not exist.
        """
        self.dbLock.acquire()
        returnValue = None
        try:
            returnValue = self.database.edges[uid]
        except KeyError:
            pass
        finally:
            self.dbLock.release()
            return returnValue

    def getIncomingLinks(self, uid: str):
        """
        Get all incoming edges for the given entity uid (primary attribute).
        """
        self.dbLock.acquire()
        returnValue = None
        if self.isNodeNoLock(uid):
            returnValue = self.database.in_edges(uid)
        self.dbLock.release()
        return returnValue

    def getOutgoingLinks(self, uid: str):
        """
        Get all outgoing edges for the given entity uid (primary attribute).
        """
        self.dbLock.acquire()
        returnValue = None
        if self.isNodeNoLock(uid):
            returnValue = self.database.out_edges(uid)
        self.dbLock.release()
        return returnValue

    def isNode(self, uid: Union[str, list, tuple]):
        """
        Returns True if the uid (primary attribute) given exists as
        an entity, and False otherwise.
        """
        self.dbLock.acquire()
        returnValue = False
        if isinstance(uid, str) and self.database.nodes.get(uid) is not None:
            returnValue = True
        self.dbLock.release()
        return returnValue

    def isNodeNoLock(self, uid: str):
        """
        Returns True if the uid (primary attribute) given exists as
        an entity, and False otherwise.

        Used only in this class, as it does not lock.
        """
        if self.database.nodes.get(uid) is not None:
            return True
        return False

    def isLink(self, uid: Union[str, list, tuple]):
        """
        Returns True if the uid given exists as a link, and False otherwise.
        """
        self.dbLock.acquire()
        returnValue = False
        if isinstance(uid, tuple) and self.database.edges.get(uid) is not None:
            returnValue = True
        self.dbLock.release()
        return returnValue

    def isLinkNoLock(self, uid: tuple) -> Union[bool, dict]:
        """
        Returns True if the uid given exists as a link, and False otherwise.
        
        Used only in this class, as it does not lock.
        """
        if self.database.edges.get(uid) is not None:
            return self.database.edges[uid]
        return False

    def getEntityType(self, uid: str):
        self.dbLock.acquire()
        returnValue = None
        try:
            returnValue = self.getEntityNoLock(uid)['Entity Type']
        except KeyError:
            pass
        finally:
            self.dbLock.release()
            return returnValue

    def mergeDatabases(self, newDB_nodes: dict, newDB_edges: dict, fromServer=True):
        """
        Merges the existing database with the one provided.
        
        Overwrites older attributes with newer ones.
        """
        self.dbLock.acquire()
        differenceGraph = nx.DiGraph()
        # Note: If we ever receive a node without a 'Date Last Edited' field, ignore it.
        differenceGraph.add_nodes_from([(x, newDB_nodes[x])
                                        for x in newDB_nodes if (x not in self.database.nodes()) or
                                        (
                                                x in self.database.nodes() and
                                                newDB_nodes[x].get('Date Last Edited') and
                                                newDB_nodes[x]['Date Last Edited'] >
                                                self.database.nodes[x]['Date Last Edited']
                                        )
                                        ])
        differenceGraph.add_edges_from([(x, y, newDB_edges[(x, y)])
                                        for x, y in newDB_edges if ((x, y) not in self.database.edges()) or
                                        (
                                                (x, y) in self.database.edges() and
                                                newDB_edges[(x, y)].get('Date Last Edited') and
                                                newDB_edges[(x, y)]['Date Last Edited'] >
                                                self.database.edges[(x, y)]['Date Last Edited']
                                        )
                                        ])
        if differenceGraph.number_of_nodes() > 0:
            self.database = nx.compose(self.database, differenceGraph)
            # Some nodes given by differenceGraph may be empty dicts, with an existing node's uid as the key.
            for node in differenceGraph.nodes:
                self.mainWindow.populateEntitiesWidget(self.database.nodes[node], add=True)

            if not fromServer:
                if self.mainWindow.FCOM.isConnected():
                    # diffNew = nx.DiGraph()
                    # diffNew.add_nodes_from([(x, self.database.nodes[x])
                    #                        for x in self.database.nodes() if x not in differenceGraph.nodes()
                    #                        ])
                    # diffNew.add_edges_from([(x, y, self.database.edges[(x, y)])
                    #                        for x, y in self.database.edges() if (x, y) not in differenceGraph.edges()
                    #                        ])

                    self.mainWindow.FCOM.syncDatabase(self.mainWindow.SETTINGS.value("Project/Server/Project"),
                                                      differenceGraph)

        self.dbLock.release()
