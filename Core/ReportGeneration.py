#!/usr/bin/env python3

from datetime import datetime
from pathlib import Path
from reportlab.lib import colors
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.graphics.charts.piecharts import Pie
from reportlab.platypus.frames import Frame
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.units import cm

from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, PageBreak, Image, Spacer, Table, LongTable, ParagraphAndImage
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.pagesizes import LETTER, inch
from reportlab.graphics.shapes import Line, Drawing

from Core.GlobalVariables import avoid_parsing_fields


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
            if style == 'Heading2':
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
        pageCountString = "Page %s of %s" % (self._pageNumber, pageCount)
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

        spacer = Spacer(100, 200)
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
        if type(entityImagePath) == Drawing:
            tbl = ReportImageAndParagraph(text, entityImagePath, side='left', xpad=10, ypad=0)
        elif entityImagePath.endswith('.png') or entityImagePath.endswith('.jpg'):
            entityImage = Image(entityImagePath, kind='proportional')
            entityImage.preserveAspectRatio = True
            entityImage.drawHeight = 2 * inch
            entityImage.drawWidth = 2 * inch
            tbl = ReportImageAndParagraph(text, entityImage, side='left', xpad=10, ypad=0)

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
            index = 0
            for link in outgoingLinks:
                resolutionText = link['Resolution']
                childNodeText = outgoingNames[index]
                linkNotesText = link['Notes']
                linkName = "".join([resolutionText[counter:counter+24] + "\n"
                                    for counter in range(0, len(resolutionText), 24)])
                childNode = "".join([childNodeText[counter:counter+24] + "\n"
                                    for counter in range(0, len(childNodeText), 24)])
                linkNotes = "".join([linkNotesText[counter:counter+24] + "\n"
                                    for counter in range(0, len(linkNotesText), 24)])
                dateCreated = link['Date Created']
                outgoing_data.append([linkName, childNode, dateCreated, Paragraph(linkNotes)])
                index += 1
            outgoing_table = Table(data=outgoing_data, style=links_table_style, hAlign="CENTER",
                                   colWidths=[140, 140, 140, 140])
            spacer = Spacer(10, 10)
            self.elements.append(spacer)
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
            index = 0
            for link in incomingLinks:
                resolutionText = link['Resolution']
                parentNodeText = incomingNames[index]
                linkNotesText = link['Notes']
                linkName = "".join([resolutionText[counter:counter+24] + "\n"
                                    for counter in range(0, len(resolutionText), 24)])
                parentNode = "".join([parentNodeText[counter:counter+24] + "\n"
                                      for counter in range(0, len(parentNodeText), 24)])
                linkNotes = "".join([linkNotesText[counter:counter+24] + "\n"
                                    for counter in range(0, len(linkNotesText), 24)])
                dateCreated = link['Date Created']
                incoming_data.append([linkName, parentNode, dateCreated, Paragraph(linkNotes)])
                index += 1
            incoming_table = Table(data=incoming_data, style=links_table_style, hAlign="CENTER",
                                   colWidths=[140, 140, 140, 140])
            spacer = Spacer(10, 10)
            self.elements.append(spacer)
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
                value = "".join([valueText[counter:counter+80] + "\n"
                                 for counter in range(0, len(valueText), 80)])
                entity_data.append([Paragraph(key, tableParagraph), Paragraph(value, tableParagraph)])
            elif key == 'Notes':
                entity_notes_header = Paragraph("Entity Notes ", notesHeader)
                entity_notes = Paragraph(entity[key], notesParagraph)
        entity_table = Table(data=entity_data, style=entity_table_style, hAlign="CENTER")

        appendix_header = Paragraph(f"Appendix {appendixNumber}", notesHeader)
        text = []
        images = []
        imangeNParagraph = []
        for appendixDict in appendixDicts:
            if appendixDict['AppendixEntityImage'] == '':
                text.append(Paragraph(appendixDict['AppendixEntityNotes'], notesParagraph))
            elif appendixDict['AppendixEntityNotes'] == '' and appendixDict['AppendixEntityImage'] != '':
                img = Image(Path(appendixDict['AppendixEntityImage']), kind='proportional')
                # img.preserveAspectRatio=True
                img.drawHeight = 2 * inch
                img.drawWidth = 2 * inch
                img.hAlign = 'LEFT'
                images.append(img)
            elif appendixDict['AppendixEntityNotes'] != '' and appendixDict['AppendixEntityImage'] != '':
                paragraph = appendixDict['AppendixEntityNotes']
                img = Image(Path(appendixDict['AppendixEntityImage']), kind='proportional')
                img.drawHeight = 2 * inch
                img.drawWidth = 2 * inch
                imangeNParagraph.append(
                    ReportImageAndParagraph(Paragraph(paragraph), img, side='left', xpad=10, ypad=0))

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
            pie.data = [int(len(incomingLinks)), int(len(outgoingLinks))]
            pie.sideLabels = 1
            pie.labels = ['Incoming: ' + str(len(incomingLinks)), 'Outgoing: ' + str(len(outgoingLinks))]
            pie.slices.strokeWidth = 1
            if int(len(incomingLinks)) > int(len(outgoingLinks)):
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
        self.elements.append(appendix_header)
        spacer = Spacer(20, 20)
        self.elements.append(spacer)
        for elementText in text:
            self.elements.append(elementText)
            self.elements.append(spacer)
        for elementImage in images:
            self.elements.append(elementImage)
            self.elements.append(spacer)
        for elementBoth in imangeNParagraph:
            self.elements.append(elementBoth)
            self.elements.append(spacer)

        self.elements.append(PageBreak())

    # Currently, does not really help very much and does not look good, so the graph page is not generated.
    def graphPage(self, timeLineImage):
        spacer = Spacer(10, 10)
        self.elements.append(spacer)

        ParagraphStyle('Report', fontSize=9, justifyBreaks=1, alignment=TA_LEFT,
                       justifyLastLine=1)

        img = Image(timeLineImage, kind='proportional')
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
            self.entityPage(title=entityPrimaryField[i - 3], userNotes=entityListData[i][0].get('EntityNotes'),
                            entityImagePath=imagePath,
                            appendixDicts=entityListData[i][1], outgoingLinks=outgoingLinks[i - 3],
                            incomingLinks=incomingLinks[i - 3],
                            entity=entity[i - 3], incomingNames=incomingNames[i - 3], outgoingNames=outgoingNames[i - 3],
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
