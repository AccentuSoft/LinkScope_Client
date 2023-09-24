#!/usr/bin/env python3

"""
Credit to @cyb_detective:
https://medium.com/@cyb_detective/20-regular-expressions-examples-to-search-for-data-related-to-cryptocurrencies-43e31dd4a5dc
"""


class CryptoAddressExtractor:
    # A string that is treated as the name of this resolution.
    name = "Extract Cryptocurrency Addresses"

    category = "Website Information"

    # A string that describes this resolution.
    description = "Returns patterns matching common cryptocurrency address formats on a website."

    originTypes = {'Domain', 'Website'}

    resultTypes = {'Crypto Wallet'}

    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from playwright.sync_api import sync_playwright, TimeoutError, Error
        from bs4 import BeautifulSoup
        from pathlib import Path
        import re

        playwrightPath = Path(parameters['Playwright Chromium'])
        returnResults = []

        ethRegex = re.compile(r"\b0[xX][a-fA-F0-9]{40}\b")
        btcRegex = re.compile(
            r"\b(?:bc(?:0(?:[ac-hj-np-z02-9]{39}|[ac-hj-np-z02-9]{59})|1[ac-hj-np-z02-9]{8,87})|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b")
        bchRegex = re.compile(r"\b(?:(?:bitcoincash|bchreg|bchtest):)?[qp][a-z0-9]{41}\b")
        moneroRegex = re.compile(r"\b[48][0-9AB][1-9A-HJ-NP-Za-km-z]{93}\b")
        dogeRegex = re.compile(r"\bD[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}\b")
        dashRegex = re.compile(r"\bX[1-9A-HJ-NP-Za-km-z]{33}\b")
        rippleRegex = re.compile(r"\br[1-9A-HJ-NP-Za-km-z]{24,34}\b")
        neoRegex = re.compile(r"\bN[0-9a-zA-Z]{33}\b")
        litecoinRegex = re.compile(r"\b[LM3][a-km-zA-HJ-NP-Z1-9]{26,33}\b")
        cosmosRegex = re.compile(r"\bcosmos[a-zA-Z0-9_.-]{10,}\b")
        cardanoRegex = re.compile(r"\baddr1[a-z0-9]{10,}\b")
        iotaRegex = re.compile(r"\biota[a-z0-9]{10,}\b")
        liskRegex = re.compile(r"\b[0-9]{19}L\b")
        nemRegex = re.compile(
            r"\bN[A-Za-z0-9]{4,7}-[A-Za-z0-9]{4,7}-[A-Za-z0-9]{4,7}-[A-Za-z0-9]{4,7}-[A-Za-z0-9]{4,7}-[A-Za-z0-9]{4,7}-[A-Za-z0-9]{4,7}\b")
        ontologyRegex = re.compile(r"\bA[0-9a-zA-Z]{33}\b")
        polkadotRegex = re.compile(r"\b1[0-9a-zA-Z]{47}\b")
        stellarRegex = re.compile(r"\bG[0-9A-Z]{55}\b")  # Stellar addresses are always 56 characters long.

        # The software can deduplicate, but handling it here is better.
        allWallets = set()

        def extractCryptoAddresses(currentUID: str, site: str):
            page = context.new_page()
            pageResolved = False
            for _ in range(3):
                try:
                    page.goto(site, wait_until="networkidle", timeout=10000)
                    pageResolved = True
                    break
                except TimeoutError:
                    pass
                except Error:
                    break
            if not pageResolved:
                # Last chance for this to work; some pages have issues with the "networkidle" trigger.
                try:
                    page.goto(site, wait_until="load", timeout=10000)
                except Error:
                    return

            soupContents = BeautifulSoup(page.content(), 'lxml')
            # Remove <span> and <noscript> tags.
            while True:
                try:
                    soupContents.noscript.extract()
                except AttributeError:
                    break
            while True:
                try:
                    soupContents.span.extract()
                except AttributeError:
                    break
            siteContent = soupContents.get_text()

            ethMatch = ethRegex.findall(siteContent)
            for potentialMatch in ethMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Etherium',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Etherium Wallet Address',
                                                        'Notes': ''}}])
            btcMatch = btcRegex.findall(siteContent)
            for potentialMatch in btcMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Bitcoin',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Bitcoin or Bitcoin Cash Wallet Address',
                                                        'Notes': ''}}])
            bchMatch = bchRegex.findall(siteContent)
            for potentialMatch in bchMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Bitcoin Cash',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Bitcoin Cash Wallet Address',
                                                        'Notes': ''}}])
            xmrMatch = moneroRegex.findall(siteContent)
            for potentialMatch in xmrMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Monero',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Monero Wallet Address',
                                                        'Notes': ''}}])
            dogeMatch = dogeRegex.findall(siteContent)
            for potentialMatch in dogeMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Dogecoin',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Dogecoin Wallet Address',
                                                        'Notes': ''}}])
            dashMatch = dashRegex.findall(siteContent)
            for potentialMatch in dashMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Dash',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Dash Wallet Address',
                                                        'Notes': ''}}])
            rippleMatch = rippleRegex.findall(siteContent)
            for potentialMatch in rippleMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Ripple',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Ripple Wallet Address',
                                                        'Notes': ''}}])
            neoMatch = neoRegex.findall(siteContent)
            for potentialMatch in neoMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Neo',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Neo Wallet Address',
                                                        'Notes': ''}}])
            litecoinMatch = litecoinRegex.findall(siteContent)
            for potentialMatch in litecoinMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Litecoin',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Litecoin Wallet Address',
                                                        'Notes': ''}}])
            cosmosMatch = cosmosRegex.findall(siteContent)
            for potentialMatch in cosmosMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Cosmos',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Cosmos Wallet Address',
                                                        'Notes': ''}}])
            cardanoMatch = cardanoRegex.findall(siteContent)
            for potentialMatch in cardanoMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Cardano',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Cardano Wallet Address',
                                                        'Notes': ''}}])
            iotaMatch = iotaRegex.findall(siteContent)
            for potentialMatch in iotaMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Iota',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Iota Wallet Address',
                                                        'Notes': ''}}])
            liskMatch = liskRegex.findall(siteContent)
            for potentialMatch in liskMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Lisk',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Lisk Wallet Address',
                                                        'Notes': ''}}])
            nemMatch = nemRegex.findall(siteContent)
            for potentialMatch in nemMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Nem',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Nem Wallet Address',
                                                        'Notes': ''}}])
            ontologyMatch = ontologyRegex.findall(siteContent)
            for potentialMatch in ontologyMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Ontology',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Ontology Wallet Address',
                                                        'Notes': ''}}])
            polkadotMatch = polkadotRegex.findall(siteContent)
            for potentialMatch in polkadotMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Polkadot',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Polkadot Wallet Address',
                                                        'Notes': ''}}])
            stellarMatch = stellarRegex.findall(siteContent)
            for potentialMatch in stellarMatch:
                if potentialMatch not in allWallets:
                    allWallets.add(potentialMatch)
                    returnResults.append([{'Wallet Address': potentialMatch,
                                           'Currency Name': 'Stellar',
                                           'Entity Type': 'Crypto Wallet'},
                                          {currentUID: {'Resolution': 'Potential Stellar Wallet Address',
                                                        'Notes': ''}}])

        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=playwrightPath)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) '
                           'Chrome/101.0.4951.54 Safari/537.36'
            )
            for entity in entityJsonList:
                uid = entity['uid']
                url = entity.get('URL') if entity.get('Entity Type', '') == 'Website' else \
                    entity.get('Domain Name', None)
                if url is None:
                    continue
                if not url.startswith('http://') and not url.startswith('https://'):
                    url = f'http://{url}'
                extractCryptoAddresses(uid, url)
            browser.close()

        return returnResults
