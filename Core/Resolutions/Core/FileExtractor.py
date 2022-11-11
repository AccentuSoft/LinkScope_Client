#!/usr/bin/env python3

"""
It should be noted that the effectiveness of this resolution relies on the website in question to have the non-website
documents showing their extension in their links in the page. Since the extension is available the vast majority of the
time, the resolution should produce correct results just about every time.

The alternative is to analyze the contents of each page to determine if they are a non-web file, and then initiate a
download. This would require a lot of work for very little payoff, which would be error-prone in and of itself, so it
is not pursued.

A few sites may also present issues when downloads are attempted by a user agent without javascript.
Even if the download does not work however, the site containing the file will be represented as a node on the graph,
so the user can download the file themselves if there was any issue.
"""


class FileExtractor:
    # A string that is treated as the name of this resolution.
    name = "Find Hosted File URLs"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Returns Nodes of files in websites and domains."

    originTypes = {'Domain', 'Website'}

    resultTypes = {'Website', 'Document', 'Spreadsheet', 'Image', 'Video', 'Archive'}

    parameters = {'Max Depth': {'description': 'Each link leading to another website in the same domain can be '
                                               'explored to discover more entities. Each entity discovered after '
                                               'exploring sites linked in the original website or domain is said to '
                                               'have a "depth" value of 1. Entities found from exploring the links on '
                                               'this page would have a "depth" of 2, and so on. A larger value could '
                                               'result in EXPONENTIALLY more time taken to finish the resolution.\n'
                                               'The default value is "0", which means only the provided website, or '
                                               'the index page of the domain provided, is explored.',
                                'type': 'String',
                                'value': '0',
                                'default': '0'}}

    def resolution(self, entityJsonList, parameters):
        import contextlib
        import tldextract
        import requests
        from hashlib import md5
        from binascii import hexlify
        from pathlib import Path
        from bs4 import BeautifulSoup
        from playwright.sync_api import sync_playwright, TimeoutError, Error

        try:
            maxDepth = max(int(parameters['Max Depth']), 0)
        except ValueError:
            return "Invalid value provided for Max Webpages to follow."

        fileTypes = (".sxw", ".odt", ".odg", ".odp", ".docx", ".pptx", ".ppsx", ".doc", ".csv",
                     ".ppt", ".pps", ".pdf", ".wpd", ".raw", ".cr2", ".crw", ".indd", ".rdp", ".ica", ".ico", ".txt",
                     ".text", ".bak", ".log", ".env", ".pub", ".docm", ".old", ".apk", ".sql", ".cfg",
                     ".key", ".reg", ".yml", ".yaml", ".mail", ".eml", ".mbox", ".mbx", ".url", ".csr", ".config",
                     ".mdb", ".user", ".adr", ".ini", ".plist", ".conf", ".dat", ".pcf", ".bok", ".properties", ".json",
                     ".backup", ".sh", ".py", ".md", ".inc")
        spreadsheetTypes = (".xlsx", ".xls", ".ods", ".xlsm")
        videoTypes = (".mp3", ".mp4")
        imageTypes = (".jpg", ".jpeg", ".png", ".svg", ".svgz")
        archiveTypes = (".zip", ".rar", ".7z", ".gz")

        returnResults = []

        def iterateOnDepth(currentURL, currentDepth: int):
            urlsExplored.add(currentURL)
            urlsToExplore = set()

            for _ in range(3):
                try:
                    page.goto(currentURL, wait_until="networkidle", timeout=10000)
                    break
                except TimeoutError:
                    pass
                except Error:
                    break

            soupContents = BeautifulSoup(page.content(), 'lxml')

            urlInPage = soupContents.find_all('a') + soupContents.find_all('link')
            for tag in urlInPage:
                link = tag.get('href', None)
                if link is not None:
                    if not link.startswith('http'):
                        # We assume that we will be redirected to https if available.
                        link = f'http://{domain}{link}'
                    link = link.split('#')[0]
                    if link not in urlsExplored:
                        urlsExplored.add(link)

                        fileTypeIdentified = ''

                        # Material name is the part after the last slash of the URL, plus the sha512sum of the URL
                        if link.endswith(fileTypes):
                            fileTypeIdentified = 'Document'
                        elif link.endswith(videoTypes):
                            fileTypeIdentified = 'Video'
                        elif link.endswith(imageTypes):
                            fileTypeIdentified = 'Image'
                        elif link.endswith(archiveTypes):
                            fileTypeIdentified = 'Archive'
                        elif link.endswith(spreadsheetTypes):
                            fileTypeIdentified = 'Spreadsheet'

                        if fileTypeIdentified:
                            childIndex = len(returnResults)

                            returnResults.append([{'URL': link,
                                                   'Entity Type': 'Website'},
                                                  {uid: {'Resolution': 'File URL',
                                                         'Notes': ''}}])

                            docProperName = link.split('/')[-1]
                            docFileName = f'{hexlify(md5(link.encode()).digest()).decode()} | {docProperName}'
                            docFullPath = Path(parameters['Project Files Directory']) / docFileName

                            with contextlib.suppress(Exception):
                                response = requests.get(link,
                                                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; '
                                                                               'x64; rv:94.0) Gecko/20100101 '
                                                                               'Firefox/94.0'},
                                                        stream=True)
                                with open(docFullPath, 'wb') as fileToWrite:
                                    for chunk in response.iter_content(4096):
                                        fileToWrite.write(chunk)

                                returnResults.append([{f'{fileTypeIdentified} Name': docProperName,
                                                       'File Path': docFileName,
                                                       'Entity Type': fileTypeIdentified},
                                                      {childIndex: {'Resolution': 'Downloaded File', 'Notes': ''}}])

                        elif domain in link:
                            urlsToExplore.add(link)

            linksInImgSrc = soupContents.find_all('img')
            for tag in linksInImgSrc:
                link = tag.get('src', None)
                if link is not None:
                    if not link.startswith('http'):
                        # We assume that we will be redirected to https if available.
                        link = f'http://{domain}{link}'
                    link = link.split('#')[0]
                    if link not in urlsExplored:
                        urlsExplored.add(link)

                        childIndex = len(returnResults)

                        returnResults.append([{'URL': link,
                                               'Entity Type': 'Website'},
                                              {uid: {'Resolution': 'File URL',
                                                     'Notes': ''}}])
                        docProperName = link.split('/')[-1]
                        docFileName = f'{hexlify(md5(link.encode()).digest()).decode()} | {docProperName}'
                        docFullPath = Path(parameters['Project Files Directory']) / docFileName

                        with contextlib.suppress(Exception):
                            response = requests.get(link,
                                                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; '
                                                                           'x64; rv:94.0) Gecko/20100101 '
                                                                           'Firefox/94.0'},
                                                    stream=True)
                            with open(docFullPath, 'wb') as fileToWrite:
                                for chunk in response.iter_content(4096):
                                    fileToWrite.write(chunk)

                            returnResults.append([{'Image Name': docProperName,
                                                   'File Path': docFileName,
                                                   'Entity Type': 'Image'},
                                                  {childIndex: {'Resolution': 'Downloaded File',
                                                                'Notes': ''}}])
            if currentDepth > 0:
                newDepth = currentDepth - 1
                for newURL in urlsToExplore:
                    iterateOnDepth(newURL, newDepth)

        with sync_playwright() as p:
            browser = p.firefox.launch()
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0'
            )
            page = context.new_page()
            for site in entityJsonList:
                uid = site['uid']
                url = site.get('URL') if site.get('Entity Type', '') == 'Website' else site.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = f'http://{url}'
                domain = tldextract.extract(url).fqdn

                # Because these do not persist across entities, it is possible to explore a URL multiple times.
                # However, since different URLs may be encountered at different depths, this way should ensure
                #   that there are no false negatives, i.e. if something should be discovered, it will be.
                urlsExplored = set()
                iterateOnDepth(url, maxDepth)

            return returnResults
