#!/usr/bin/env python3

import tempfile
import re
from shutil import rmtree
from svglib.svglib import svg2rlg
from uuid import uuid4
from datetime import datetime
from pathlib import Path
from reportlab.lib import colors
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.graphics.charts.piecharts import Pie
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.units import cm

from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, PageBreak, Image, Spacer, Table, ParagraphAndImage
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER, inch
from reportlab.graphics.shapes import Line, Drawing
from PySide6 import QtWidgets

from Core.Interface.Entity import BaseNode
from Core.GlobalVariables import avoid_parsing_fields


class ReportWizard(QtWidgets.QWizard):
    def __init__(self, parent):
        super(ReportWizard, self).__init__(parent=parent)
        self.reportTempFolder = tempfile.mkdtemp()

        self.primaryFieldsList = []

        self.addPage(InitialConfigPage(self))
        self.addPage(TitlePage(self))

        self.addPage(SummaryPage(self))

        self.selectedNodes = [entity for entity in
                              self.parent().centralWidget().tabbedPane.getCurrentScene().selectedItems()
                              if isinstance(entity, BaseNode)]
        for selectedNode in self.selectedNodes:
            # used in wizard
            self.primaryField = selectedNode.labelItem.toPlainText()
            self.uid = selectedNode.uid

            # used in report generation
            self.primaryFieldsList.append(self.primaryField)
            self.addPage(EntityPage(self))

        self.setWizardStyle(QtWidgets.QWizard.WizardStyle.ModernStyle)
        self.setWindowTitle("Generate Report Wizard")

        self.button(QtWidgets.QWizard.WizardButton.FinishButton).clicked.connect(self.onFinish)

    def onFinish(self):
        outgoingEntitiesForEachEntity = []
        incomingEntitiesForEachEntity = []
        outgoingEntityPrimaryFieldsForEachEntity = []
        incomingEntityPrimaryFieldsForEachEntity = []

        entityList = []
        reportData = []
        for pageID in self.pageIds():
            pageObject = self.page(pageID)
            reportData.append(pageObject.getData())

        for selectedNode in self.selectedNodes:
            uid = selectedNode.uid
            entityList.append(self.parent().LENTDB.getEntity(uid))
            outgoing = self.parent().LENTDB.getOutgoingLinks(uid)
            incoming = self.parent().LENTDB.getIncomingLinks(uid)

            outgoingEntities = []
            incomingEntities = []
            outgoingNames = []
            incomingNames = []

            for out in outgoing:
                outLink = self.parent().LENTDB.getLink(out)
                outgoingEntities.append(outLink)
                outgoingEntityJson = self.parent().LENTDB.getEntity(outLink['uid'][1])
                outgoingNames.append(outgoingEntityJson[list(outgoingEntityJson)[1]])

            for inc in incoming:
                inLink = self.parent().LENTDB.getLink(inc)
                incomingEntities.append(inLink)
                incomingEntityJson = self.parent().LENTDB.getEntity(inLink['uid'][0])

                incomingNames.append(incomingEntityJson[list(incomingEntityJson)[1]])

            outgoingEntityPrimaryFieldsForEachEntity.append(outgoingNames)
            incomingEntityPrimaryFieldsForEachEntity.append(incomingNames)
            outgoingEntitiesForEachEntity.append(outgoingEntities)
            incomingEntitiesForEachEntity.append(incomingEntities)

        path = Path(reportData[0].get('SavePath'))

        canvasName = reportData[2].get('CanvasName')
        viewPortBool = reportData[2].get('ViewPort')

        canvasPicture = self.parent().getPictureOfCanvas(canvasName, viewPortBool, True)
        canvasImagePath = Path(self.reportTempFolder) / 'canvas.png'
        canvasPicture.save(str(canvasImagePath), "PNG")

        # timelinePicture = self.parent().dockbarThree.timeWidget.takePictureOfView(False)
        # timelineImagePath = Path(temp_dir.name) / 'timeline.png'
        # timelinePicture.save(str(timelineImagePath), "PNG")

        savePath = Path(reportData[0]['SavePath']).absolute()

        try:
            PDFReport(str(path), reportData, outgoingEntitiesForEachEntity,
                      incomingEntitiesForEachEntity, entityList, canvasImagePath, None,  # <timelinePic
                      self.primaryFieldsList, incomingEntityPrimaryFieldsForEachEntity,
                      outgoingEntityPrimaryFieldsForEachEntity)

            self.parent().MESSAGEHANDLER.debug(reportData)
            self.parent().MESSAGEHANDLER.info(
                f"Saved Report at: {str(savePath)}", popUp=True
            )
        except PermissionError:
            self.parent().MESSAGEHANDLER.error(
                f"Could not generate report. No permission to save at the chosen location: {str(savePath)}",
                popUp=True,
                exc_info=False,
            )
        except Exception as exc:
            self.parent().MESSAGEHANDLER.error(
                f"Could not generate report: {str(exc)}", popUp=True, exc_info=True
            )
        finally:
            rmtree(self.reportTempFolder)


class InitialConfigPage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(InitialConfigPage, self).__init__(parent)
        self.subtitleLabel = QtWidgets.QLabel("Path to save the report at: ")
        self.savePathEdit = QtWidgets.QLineEdit()
        self.setTitle("Initial Configuration Wizard")

        pDirButton = QtWidgets.QPushButton("Save Report As...")
        pDirButton.clicked.connect(self.editPath)

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(self.subtitleLabel)
        hLayout.addWidget(self.savePathEdit)
        hLayout.addWidget(pDirButton)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        self.setLayout(layout)

    def editPath(self):
        selectedPath = QtWidgets.QFileDialog.getSaveFileName(self,
                                                             "File Name to Save As",
                                                             str(Path.home()),
                                                             filter="PDF Files (*.pdf)",
                                                             options=QtWidgets.QFileDialog.Option.DontUseNativeDialog)
        selectedPath = selectedPath[0]
        if selectedPath != '':
            savePath = Path(selectedPath).absolute()
            if savePath.suffix != '.pdf':
                savePath = savePath.with_suffix(f"{savePath.suffix}.pdf")
            self.savePathEdit.setText(str(savePath))

    def getData(self):
        return {'SavePath': self.savePathEdit.text()}


class TitlePage(QtWidgets.QWizardPage):
    def __init__(self, parent=None):
        super(TitlePage, self).__init__(parent)
        self.inputTitleEdit = QtWidgets.QLineEdit()
        self.inputSubtitleEdit = QtWidgets.QLineEdit()
        self.inputAuthorsEdit = QtWidgets.QLineEdit()
        self.setTitle("Title Page Wizard")

        titleLabel = QtWidgets.QLabel("Title: ")
        subtitleLabel = QtWidgets.QLabel("Subtitle: ")
        authorsLabel = QtWidgets.QLabel("Authors: ")

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(titleLabel)
        hLayout.addWidget(self.inputTitleEdit)
        hLayout.addWidget(subtitleLabel)
        hLayout.addWidget(self.inputSubtitleEdit)
        hLayout.addWidget(authorsLabel)
        hLayout.addWidget(self.inputAuthorsEdit)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        self.setLayout(layout)

    def getData(self):
        return {
            'Title': self.inputTitleEdit.text(),
            'Subtitle': self.inputSubtitleEdit.text(),
            'Authors': self.inputAuthorsEdit.text(),
        }


class SummaryPage(QtWidgets.QWizardPage):
    def __init__(self, parent):
        super(SummaryPage, self).__init__(parent=parent.parent())
        self.setTitle("Summary Page Wizard")
        self.inputNotesEdit = QtWidgets.QPlainTextEdit()
        self.canvasDropDownMenu = QtWidgets.QComboBox()
        self.viewPortCheckBox = QtWidgets.QCheckBox('ViewPort Only')
        self.viewPortCheckBox.setChecked(False)
        self.canvasNames = list(self.parent().centralWidget().tabbedPane.canvasTabs.keys())

        summaryLabel = QtWidgets.QLabel("Summary Notes: ")

        canvasLabel = QtWidgets.QLabel("Select canvas to be displayed: ")
        for canvasName in self.canvasNames:
            self.canvasDropDownMenu.addItem(canvasName)

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(summaryLabel)
        hLayout.addWidget(self.inputNotesEdit)
        hLayout.addWidget(canvasLabel)
        hLayout.addWidget(self.viewPortCheckBox)
        hLayout.addWidget(self.canvasDropDownMenu)
        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        self.setLayout(layout)

    def getData(self):
        return {
            'SummaryNotes': self.inputNotesEdit.toPlainText(),
            'CanvasName': self.canvasDropDownMenu.currentText(),
            'ViewPort': self.viewPortCheckBox.isChecked(),
        }


class EntityPage(QtWidgets.QWizardPage):
    def __init__(self, parent: ReportWizard):
        super(EntityPage, self).__init__(parent=parent.parent())
        self.reportWizard = parent

        self.setTitle("Entity Page Wizard")
        self.setMinimumSize(300, 700)

        self.entityName = parent.primaryField
        self.entityUID = parent.uid

        self.inputNotesEdit = QtWidgets.QPlainTextEdit()
        self.inputImageEdit = QtWidgets.QLineEdit()
        self.inputImageEdit.setReadOnly(True)
        self.addAppendixButton = QtWidgets.QPushButton("Add New Appendix Section")
        self.removeAppendixButton = QtWidgets.QPushButton("Remove Last Appendix Section")

        self.scrolllayout = QtWidgets.QVBoxLayout()
        self.scrollwidget = QtWidgets.QWidget()

        self.defaultpic = self.parent().LENTDB.getEntity(self.entityUID).get('Icon')

        summaryLabel = QtWidgets.QLabel(f"Entity {self.entityName} Notes: ")

        imageLabel = QtWidgets.QLabel("Image Path: ")
        pDirButton = QtWidgets.QPushButton("Select Image...")
        pDirButton.clicked.connect(self.editPath)
        pDirButton.setDisabled(True)
        self.imageCheckBox = QtWidgets.QCheckBox('Add Custom Entity Image')
        self.imageCheckBox.setChecked(False)
        self.imageCheckBox.toggled.connect(pDirButton.setEnabled)

        self.addAppendixButton.clicked.connect(self.addSection)
        self.removeAppendixButton.clicked.connect(self.removeSection)

        self.scrollwidget.setLayout(self.scrolllayout)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.scrollwidget)

        hLayout = QtWidgets.QVBoxLayout()
        hLayout.addWidget(summaryLabel)
        hLayout.addWidget(self.inputNotesEdit)

        hLayout.addWidget(self.imageCheckBox)
        hLayout.addWidget(imageLabel)
        hLayout.addWidget(self.inputImageEdit)
        hLayout.addWidget(pDirButton)

        hLayout.addItem(QtWidgets.QSpacerItem(10, 30))
        hLayout.addWidget(self.addAppendixButton)
        hLayout.addWidget(self.removeAppendixButton)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(hLayout)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def editPath(self) -> None:
        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select New Icon',
                                                               dir=str(Path.home()),
                                                               options=QtWidgets.QFileDialog.Option.DontUseNativeDialog,
                                                               filter="Image Files (*.png *.jpg)")[0]
        if selectedPath != '':
            self.inputImageEdit.setText(str(Path(selectedPath).absolute()))

    def addSection(self) -> None:
        appendixWidget = AppendixWidget()
        self.scrolllayout.addWidget(appendixWidget)

    def removeSection(self) -> None:
        if numChildren := self.scrolllayout.count():
            appendixItem = self.scrolllayout.takeAt(numChildren - 1)
            appendixItem.widget().deleteLater()

    def getData(self):
        appendixNotes = []
        if self.inputImageEdit.text() != '' and self.imageCheckBox.isChecked():
            data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': self.inputImageEdit.text()}
        elif 'PNG' in str(self.defaultpic):
            imagePath = Path(self.reportWizard.reportTempFolder) / f'{str(uuid4())}.png'
            with open(imagePath, 'wb') as tempFile:
                tempFile.write(bytearray(self.defaultpic.data()))

            data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': str(imagePath)}
        else:
            if 'svg' not in str(self.defaultpic):
                # Default picture is an SVG.
                self.defaultpic = self.reportWizard.parent().RESOURCEHANDLER.getEntityDefaultPicture(
                    self.reportWizard.parent().LENTDB.getEntity(self.entityUID)['Entity Type'])
            contents = bytearray(self.defaultpic)
            widthRegex = re.compile(b' width="\d*" ')
            for widthMatches in widthRegex.findall(self.defaultpic):
                contents = contents.replace(widthMatches, b' ')
            heightRegex = re.compile(b' height="\d*" ')
            for heightMatches in heightRegex.findall(self.defaultpic):
                contents = contents.replace(heightMatches, b' ')
            contents = contents.replace(b'<svg ', b'<svg height="150" width="150" ')

            imagePath = Path(self.reportWizard.reportTempFolder) / f'{str(uuid4())}.svg'
            with open(imagePath, 'wb') as tempFile:
                tempFile.write(contents)

            image = svg2rlg(imagePath)
            data = {'EntityNotes': self.inputNotesEdit.toPlainText(), 'EntityImage': image}

        for index in range(self.scrolllayout.count()):
            childWidget = self.scrolllayout.itemAt(index).widget()
            appendixDict = {'AppendixEntityNotes': childWidget.inputAppendixNotesEdit.toPlainText(),
                            'AppendixEntityImage': childWidget.inputAppendixImageEdit.text()}
            appendixNotes.append(appendixDict)
        return data, appendixNotes


class AppendixWidget(QtWidgets.QWidget):

    def __init__(self) -> None:
        super(AppendixWidget, self).__init__()
        appendixWidgetLayout = QtWidgets.QGridLayout()
        appendixLabelNotes = QtWidgets.QLabel("Entity Notes: ")
        self.inputAppendixNotesEdit = QtWidgets.QPlainTextEdit()
        imageAppendixLabel = QtWidgets.QLabel("Image Path: ")
        appendixButton = QtWidgets.QPushButton("Select Image...")
        appendixButton.clicked.connect(self.editAppendixPath)
        self.inputAppendixImageEdit = QtWidgets.QLineEdit()
        self.inputAppendixImageEdit.setReadOnly(True)
        appendixWidgetLayout.addWidget(appendixLabelNotes, 0, 0, 1, 1)
        appendixWidgetLayout.addWidget(self.inputAppendixNotesEdit, 2, 0, 4, 1)
        appendixWidgetLayout.addWidget(imageAppendixLabel, 7, 0, 1, 1)
        appendixWidgetLayout.addWidget(self.inputAppendixImageEdit, 9, 0, 1, 1)
        appendixWidgetLayout.addWidget(appendixButton, 11, 0, 1, 1)
        self.setLayout(appendixWidgetLayout)
        self.inputAppendixNotesEdit.setFixedHeight(100)

    def editAppendixPath(self) -> None:
        selectedPath = QtWidgets.QFileDialog().getOpenFileName(parent=self, caption='Select New Icon',
                                                               dir=str(Path.home()),
                                                               options=QtWidgets.QFileDialog.Option.DontUseNativeDialog,
                                                               filter="Image Files (*.png *.jpg)")[0]

        if selectedPath != '':
            self.inputAppendixImageEdit.setText(str(Path(selectedPath).absolute()))


class MyDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kw):
        self.allowSplitting = 0
        BaseDocTemplate.__init__(self, filename, **kw)
        template = PageTemplate('normal', [Frame(3.1 * cm, 2.5 * cm, 15 * cm, 25 * cm, id='F1')])
        self.addPageTemplates(template)

    def afterFlowable(self, flowable):
        # Registers TOC entries.
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Heading1':
                self.notify('TOCEntry', (0, text, self.page))
            elif style == 'Heading2':
                self.notify('TOCEntry', (1, text, self.page))


class ReportBuilder(canvas.Canvas):

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
        self.width, self.height = LETTER

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        pageCount = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            if self._pageNumber > 1:
                self.drawHeaderAndFooter(pageCount)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def drawHeaderAndFooter(self, pageCount):
        pageCountString = f"Page {self._pageNumber} of {pageCount}"
        self.saveState()
        self.setStrokeColorRGB(0, 0, 0)
        self.setLineWidth(0.5)
        self.line(66, 78, LETTER[0] - 66, 78)
        self.setFont('Times-Roman', 10)
        self.drawString(LETTER[0] - 128, 65, pageCountString)
        self.restoreState()


class PDFReport:

    def titlePage(self, authors, title, subtitle):  # arguments to be added: authors, title, subtitle
        headline_style = self.styleSheet["Heading5"]
        headline_style.alignment = TA_CENTER
        headline_style.fontSize = 36
        headline_style.leading = 50

        subtitle_style = self.styleSheet["BodyText"]
        subtitle_style.fontSize = 20
        subtitle_style.leading = 30
        subtitle_style.alignment = TA_CENTER

        report_title = Paragraph('Investigation Report', headline_style)
        self.elements.append(report_title)
        spacer = Spacer(5, 5)
        self.elements.append(spacer)

        report_name = Paragraph(title, headline_style)
        spacer = Spacer(10, 10)
        self.elements.append(spacer)
        self.elements.append(report_name)

        report_subtitle = Paragraph(subtitle, subtitle_style)
        spacer = Spacer(10, 10)
        self.elements.append(spacer)
        self.elements.append(report_subtitle)

        spacer = Spacer(100, 425)
        self.elements.append(spacer)

        date = datetime.now().strftime('%Y-%m-%d %H:%m:%S')
        paragraphStyleOptions = ParagraphStyle('Report', fontSize=9, leading=20, justifyBreaks=1, alignment=TA_LEFT,
                                               justifyLastLine=1)
        text = f"""Investigation Report<br/>
        Authors: {authors}<br/>
        Date: {date}<br/>
        <br/>
        """
        paragraphReportSummary = Paragraph(text, paragraphStyleOptions)
        self.elements.append(paragraphReportSummary)
        self.elements.append(PageBreak())

    def summaryPage(self, userSummary, summaryCanvasImage):  # arguments: user summary input
        spacer = Spacer(10, 10)
        self.elements.append(spacer)

        paragraphStyleOptions = ParagraphStyle('Report', fontSize=9, justifyBreaks=1, alignment=TA_JUSTIFY,
                                               justifyLastLine=0)
        text = userSummary
        paragraphReportSummary = Paragraph(text, paragraphStyleOptions)

        # path to image needed
        img = Image(summaryCanvasImage)
        img.preserveAspectRatio = True
        img._restrictSize(6.5 * inch, 5.5 * inch)
        # img.drawHeight = 5.5 * inch
        # img.drawWidth = 6.5 * inch
        img.hAlign = 'CENTER'

        self.elements.append(paragraphReportSummary)
        spacer = Spacer(30, 30)
        self.elements.append(spacer)

        self.elements.append(img)
        self.elements.append(PageBreak())

    def entityPage(self, userNotes, entityImagePath, appendixDicts, outgoingLinks, incomingLinks, entity,
                   outgoingNames, incomingNames, title, appendixNumber):
        # dict with image and notes for appendix

        COLORBLACK = colors.HexColor(0x241F20)

        entity_notes_header = ''
        entity_notes = ''

        spacer = Spacer(10, 10)
        self.elements.append(spacer)

        entity_style = self.styleSheet["Title"]
        entity_style.fontSize = 24
        entity_style.leading = 20
        entity_style.alignment = TA_CENTER
        entity_style.fontName = 'Times-Bold'

        psSubHeaderText = ParagraphStyle('Heading2', fontSize=12, alignment=TA_CENTER, borderWidth=1,
                                         fontName='Times-Bold')
        notesParagraph = ParagraphStyle('Report', fontSize=9, justifyBreaks=0, alignment=TA_JUSTIFY, justifyLastLine=0)

        entityTitle = Paragraph(title, entity_style)

        notes = f"""
        <font name="Times-Bold" size="12"> User's Notes:</font><br/> {userNotes} 

        """

        text = Paragraph(notes, notesParagraph)
        if isinstance(entityImagePath, Drawing):
            tbl = ReportImageAndParagraph(text, entityImagePath, side='left', xpad=10, ypad=0)
        elif entityImagePath.endswith('.png') or entityImagePath.endswith('.jpg'):
            entityImage = Image(entityImagePath)
            entityImage.preserveAspectRatio = True
            entityImage.drawHeight = 2 * inch
            entityImage.drawWidth = 2 * inch
            tbl = ReportImageAndParagraph(text, entityImage, side='left', xpad=10, ypad=0)
        else:
            raise ValueError('Invalid Image Type')

        links_subHeader = Paragraph("Entity Links", psSubHeaderText)

        entity_summary_subHeader = Paragraph("Entity Summary", psSubHeaderText)

        links_table_style = [('GRID', (0, 0), (-1, -1), 1, COLORBLACK), ('SPAN', (3, 0), (0, 0)),
                             ('LINEABOVE', (0, 2), (-1, 2), 1, colors.blue),
                             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                             ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]

        # child UID
        if outgoingLinks:
            outgoing_data = [
                ['Outgoing Links'],
                ['Resolution Name', 'Child Entity', 'Date Created', 'Notes']]
            for index, link in enumerate(outgoingLinks):
                resolutionText = link['Resolution']
                childNodeText = outgoingNames[index]
                linkNotesText = link['Notes']
                dateCreatedText = link['Date Created']
                linkName = "".join([resolutionText[counter:counter + 24] + "\n"
                                    for counter in range(0, len(resolutionText), 24)])
                childNode = "".join([childNodeText[counter:counter + 24] + "\n"
                                     for counter in range(0, len(childNodeText), 24)])
                linkNotes = "".join([linkNotesText[counter:counter + 24] + "\n"
                                     for counter in range(0, len(linkNotesText), 24)])
                dateCreated = "".join([dateCreatedText[counter:counter + 24] + "\n"
                                       for counter in range(0, len(dateCreatedText), 24)])
                outgoing_data.append([linkName, childNode, dateCreated, Paragraph(linkNotes)])
            outgoing_table = Table(data=outgoing_data, style=links_table_style, hAlign="CENTER",
                                   colWidths=[140, 140, 140, 140])
        else:
            outgoing_data = [
                ['No Outgoing Links']]
            outgoing_table = Table(data=outgoing_data, hAlign="CENTER")
        spacer = Spacer(10, 10)
        self.elements.append(spacer)

        # parent UID
        if incomingLinks:
            incoming_data = [
                ['Incoming Links'],
                ['Resolution Name', 'Parent Entity', 'Date Created', 'Notes']]
            for index, link in enumerate(incomingLinks):
                resolutionText = link['Resolution']
                parentNodeText = incomingNames[index]
                linkNotesText = link['Notes']
                dateCreatedText = link['Date Created']
                linkName = "".join([resolutionText[counter:counter + 24] + "\n"
                                    for counter in range(0, len(resolutionText), 24)])
                parentNode = "".join([parentNodeText[counter:counter + 24] + "\n"
                                      for counter in range(0, len(parentNodeText), 24)])
                linkNotes = "".join([linkNotesText[counter:counter + 24] + "\n"
                                     for counter in range(0, len(linkNotesText), 24)])
                dateCreated = "".join([dateCreatedText[counter:counter + 24] + "\n"
                                       for counter in range(0, len(dateCreatedText), 24)])
                incoming_data.append([linkName, parentNode, dateCreated, Paragraph(linkNotes)])
            incoming_table = Table(data=incoming_data, style=links_table_style, hAlign="CENTER",
                                   colWidths=[140, 140, 140, 140])
        else:
            incoming_data = [
                ['No Incoming Links']]
            incoming_table = Table(data=incoming_data, hAlign="CENTER")
        spacer = Spacer(10, 10)
        self.elements.append(spacer)

        tableParagraph = ParagraphStyle('Report', fontSize=9, justifyBreaks=1, alignment=TA_CENTER,
                                        justifyLastLine=0)

        ParagraphStyle('Heading2', fontSize=11, justifyBreaks=1, alignment=TA_CENTER,
                       justifyLastLine=1, fontName='Times-Bold', rightIndent=45)
        notesHeader = ParagraphStyle('Heading2', fontSize=11, justifyBreaks=1, alignment=TA_CENTER,
                                     justifyLastLine=1, fontName='Times-Bold')
        entity_data = [
            ['Entity Fields'],
            ['Attribute', 'Value']]
        entity_table_style = [('GRID', (0, 0), (-1, -1), 1, COLORBLACK), ('SPAN', (1, 0), (0, 0)),
                              ('LINEABOVE', (0, 2), (-1, 2), 1, colors.blue),
                              ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]
        for key in list(entity):
            if key not in avoid_parsing_fields and key != 'Notes':
                valueText = entity[key]
                value = "".join([valueText[counter:counter + 80] + "\n"
                                 for counter in range(0, len(valueText), 80)])
                entity_data.append([Paragraph(key, tableParagraph), Paragraph(value, tableParagraph)])
            elif key == 'Notes':
                entity_notes_header = Paragraph("Entity Notes ", notesHeader)
                entity_notes = Paragraph(entity[key], notesParagraph)
        entity_table = Table(data=entity_data, style=entity_table_style, hAlign="CENTER")

        self.elements.append(entityTitle)
        spacer = Spacer(20, 20)
        self.elements.append(spacer)

        self.elements.append(tbl)
        # self.elements.append(img)
        spacer = Spacer(30, 30)
        self.elements.append(spacer)
        self.elements.append(links_subHeader)
        spacer = Spacer(15, 15)
        self.elements.append(spacer)
        self.elements.append(incoming_table)
        spacer = Spacer(25, 25)
        self.elements.append(spacer)
        self.elements.append(outgoing_table)

        if not incomingLinks and not outgoingLinks:
            # No links to draw link pie graph.
            pass
        else:
            pieDraw = Drawing()
            pie = Pie()
            pie.x = 150
            pie.y = 65
            pie.data = [len(incomingLinks), len(outgoingLinks)]
            pie.sideLabels = 1
            pie.labels = [f'Incoming: {len(incomingLinks)}', f'Outgoing: {len(outgoingLinks)}']
            pie.slices.strokeWidth = 1
            if len(incomingLinks) > len(outgoingLinks):
                pie.slices[0].popout = 5
            else:
                pie.slices[1].popout = 5
            pieDraw.add(pie)
            self.elements.append(pieDraw)

        self.elements.append(entity_summary_subHeader)
        spacer = Spacer(15, 15)
        self.elements.append(spacer)
        self.elements.append(entity_table)
        self.elements.append(spacer)
        self.elements.append(entity_notes_header)
        self.elements.append(entity_notes)
        self.elements.append(spacer)

        spacer = Spacer(20, 20)
        for appendixIndex, appendixDict in enumerate(appendixDicts):
            appendix_header = Paragraph(f"Entity Appendix {appendixIndex}", notesHeader)
            self.elements.append(appendix_header)
            self.elements.append(spacer)

            appendixImage = appendixDict['AppendixEntityImage']
            appendixNotes = appendixDict['AppendixEntityNotes']
            if appendixImage == '':
                self.elements.append(Paragraph(appendixNotes, notesParagraph))
            elif appendixNotes == '' and appendixImage != '':
                img = Image(Path(appendixImage))
                # img.preserveAspectRatio = True
                img.drawHeight = 3 * inch
                img.drawWidth = 3 * inch
                self.elements.append(img)
            elif appendixNotes != '' and appendixImage != '':
                paragraph = appendixNotes
                img = Image(Path(appendixImage))
                img.drawHeight = 3 * inch
                img.drawWidth = 3 * inch
                self.elements.append(ReportImageAndParagraph(Paragraph(paragraph), img, side='left', xpad=10, ypad=0))
            self.elements.append(spacer)

        self.elements.append(PageBreak())

    # Currently, does not really help very much and does not look good, so the graph page is not generated.
    def graphPage(self, timeLineImage):
        spacer = Spacer(10, 10)
        self.elements.append(spacer)

        ParagraphStyle('Report', fontSize=9, justifyBreaks=1, alignment=TA_LEFT,
                       justifyLastLine=1)

        img = Image(timeLineImage)
        img.drawHeight = 1.3 * inch
        img.drawWidth = 6 * inch
        img.hAlign = 'LEFT'

        spacer = Spacer(30, 30)
        self.elements.append(spacer)
        self.elements.append(img)
        self.elements.append(PageBreak())

    def nextPagesHeader(self, isSecondPage, header):
        if isSecondPage:
            psHeaderText = ParagraphStyle('Heading1', fontSize=14, alignment=TA_LEFT, borderWidth=1)
            h = header
            paragraphReportHeader = Paragraph(h, psHeaderText)
            self.elements.append(paragraphReportHeader)

            spacer = Spacer(10, 10)
            self.elements.append(spacer)

            d = Drawing(500, 1)
            line = Line(-15, 0, 430, 0)
            line.strokeWidth = 2
            d.add(line)
            self.elements.append(d)

            spacer = Spacer(10, 1)
            self.elements.append(spacer)

            d = Drawing(500, 1)
            line = Line(-15, 0, 430, 0)
            line.strokeWidth = 0.5
            d.add(line)
            self.elements.append(d)

    def __init__(self, path: str, entityListData, outgoingLinks, incomingLinks, entity, summaryCanvasImage,
                 timelineImage, entityPrimaryField, incomingNames, outgoingNames):
        self.path = path
        self.styleSheet = getSampleStyleSheet()
        self.elements = []

        self.titlePage(authors=entityListData[1].get('Authors'), title=entityListData[1].get('Title'),
                       subtitle=entityListData[1].get('Subtitle'))

        tocHeaderStyle = ParagraphStyle('Title', fontSize=16, alignment=TA_CENTER, borderWidth=1)
        tocTitle = Paragraph('Table of Contents', tocHeaderStyle)
        h1 = ParagraphStyle(name='Heading1',
                            fontSize=14,
                            leading=16)
        h2 = ParagraphStyle(name='Heading2',
                            fontSize=12,
                            leading=14, )

        toc = TableOfContents()
        toc.levelStyles = [h1, h2]
        self.elements.append(tocTitle)
        spacer = Spacer(15, 15)
        self.elements.append(spacer)
        self.elements.append(toc)
        self.elements.append(PageBreak())

        head = 'Summary Report'
        self.nextPagesHeader(True, head)

        self.summaryPage(userSummary=entityListData[2].get('SummaryNotes'), summaryCanvasImage=summaryCanvasImage)

        imagePath = ''
        for i in range(3, len(entityListData)):
            if entityListData[i][0].get('EntityImage') != '':
                imagePath = entityListData[i][0].get('EntityImage')

            head = f'Entity Report: {entityPrimaryField[i - 3]}'
            self.nextPagesHeader(True, head)
            self.entityPage(title=entityPrimaryField[i - 3],
                            userNotes=entityListData[i][0].get('EntityNotes'),
                            entityImagePath=imagePath,
                            appendixDicts=entityListData[i][1],
                            outgoingLinks=outgoingLinks[i - 3],
                            incomingLinks=incomingLinks[i - 3],
                            entity=entity[i - 3],
                            incomingNames=incomingNames[i - 3],
                            outgoingNames=outgoingNames[i - 3],
                            appendixNumber=i - 3)

        # Graph report stuff disabled, at least for now.
        # head = 'Graph Report'
        # self.nextPagesHeader(True, head)
        # self.graphPage(timelineImage)

        # Build
        self.doc = MyDocTemplate(path)
        self.doc.multiBuild(self.elements, canvasmaker=ReportBuilder)


# Subclass ParagraphAndImage to adjust the alignment of the text with the image in the element.
class ReportImageAndParagraph(ParagraphAndImage):

    def __init__(self, P, I, xpad=3, ypad=3, side='right'):
        super().__init__(P, I, xpad, ypad, side)
        self.hI = ''
        self.wI = ''
        self._offsets = ''

    def wrap(self, availWidth, availHeight):
        wI, hI = self.I.wrap(availWidth, availHeight)
        self.hI = hI
        self.wI = wI
        # work out widths array for breaking
        self.width = availWidth
        P = self.P
        style = P.style
        xpad = self.xpad
        ypad = self.ypad
        leading = style.leading
        leftIndent = style.leftIndent
        later_widths = availWidth - leftIndent - style.rightIndent
        intermediate_widths = later_widths - xpad - wI
        first_line_width = intermediate_widths - style.firstLineIndent
        P.width = 0
        nIW = int((hI + ypad) / (leading * 1.0))
        P.blPara = P.breakLines([first_line_width] + nIW * [intermediate_widths] + [later_widths])
        if self._side == 'left':
            self._offsets = [wI + xpad] * (1 + nIW) + [0]
        # Make the paragraph line up with the top part of the image if its height is less than
        #   the height of the image.
        P.height = max(hI, len(P.blPara.lines) * leading)
        self.height = max(hI, P.height)
        return self.width, self.height
