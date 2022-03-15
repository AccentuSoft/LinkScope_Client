#!/usr/bin/env python3

"""
Credit:
Twitter : @palenath
Github : https://github.com/megadose/holehe
For BTC Donations : 1FHDM49QfZX6pJmhjLE5tB2K6CaTLMZpXZ
"""


class Holehe_Account_Discovery:
    name = "Holehe Account Discovery"
    category = "Online Identity"
    description = "Discover Social Media Accounts associated with an Email Address."
    originTypes = {'Email Address'}
    resultTypes = {'Email Address', 'Phone Number', 'Phrase', 'Date', 'Domain'}
    parameters = {'Use Password Recovery Methods': {'description': 'This option dictates whether the module checks '
                                                                   'for the existence for an account in services where '
                                                                   'the way to determine if an account was registered '
                                                                   'is to attempt password recovery. This may, in '
                                                                   'certain cases, have a chance of alerting the '
                                                                   'owner of the account.',
                                                    'type': 'SingleChoice',
                                                    'value': {'Yes', 'No'}
                                                    }}

    def resolution(self, entityJsonList, parameters):
        import httpx
        from time import sleep
        from multiprocessing import Process, Queue
        from queue import Empty
        from holehe import core as holehe_core

        data = {'aboutme': 'about.me', 'adobe': 'adobe.com', 'amazon': 'amazon.com', 'anydo': 'any.do',
                'archive': 'archive.org', 'armurerieauxerre': 'armurerie-auxerre.com', 'atlassian': 'atlassian.com',
                'babeshows': 'babeshows.co.uk', 'badeggsonline': 'badeggsonline.com', 'biosmods': 'bios-mods.com',
                'biotechnologyforums': 'biotechnologyforums.com', 'bitmoji': 'bitmoji.com',
                'blablacar': 'blablacar.com', 'blackworldforum': 'blackworldforum.com', 'blip': 'blip.fm',
                'blitzortung': 'forum.blitzortung.org', 'bluegrassrivals': 'bluegrassrivals.com',
                'bodybuilding': 'bodybuilding.com', 'buymeacoffee': 'buymeacoffee.com',
                'cambridgemt': 'discussion.cambridge-mt.com', 'caringbridge': 'caringbridge.org',
                'chinaphonearena': 'chinaphonearena.com', 'clashfarmer': 'clashfarmer.com',
                'codecademy': 'codecademy.com', 'codeigniter': 'forum.codeigniter.com', 'codepen': 'codepen.io',
                'coroflot': 'coroflot.com', 'cpaelites': 'cpaelites.com', 'cpahero': 'cpahero.com',
                'cracked_to': 'cracked.to', 'crevado': 'crevado.com', 'deliveroo': 'deliveroo.com',
                'demonforums': 'demonforums.net', 'devrant': 'devrant.com', 'diigo': 'diigo.com',
                'discord': 'discord.com', 'docker': 'docker.com', 'dominosfr': 'dominos.fr', 'ebay': 'ebay.com',
                'ello': 'ello.co', 'envato': 'envato.com', 'eventbrite': 'eventbrite.com',
                'evernote': 'evernote.com', 'fanpop': 'fanpop.com', 'firefox': 'firefox.com',
                'flickr': 'flickr.com', 'freelancer': 'freelancer.com',
                'freiberg': 'drachenhort.user.stunet.tu-freiberg.de', 'garmin': 'garmin.com',
                'github': 'github.com', 'google': 'google.com', 'gravatar': 'gravatar.com', 'imgur': 'imgur.com',
                'instagram': 'instagram.com', 'issuu': 'issuu.com', 'koditv': 'forum.kodi.tv',
                'komoot': 'komoot.com', 'laposte': 'laposte.fr', 'lastfm': 'last.fm', 'lastpass': 'lastpass.com',
                'mail_ru': 'mail.ru', 'mybb': 'community.mybb.com', 'myspace': 'myspace.com',
                'nattyornot': 'nattyornotforum.nattyornot.com', 'naturabuy': 'naturabuy.fr',
                'ndemiccreations': 'forum.ndemiccreations.com', 'nextpvr': 'forums.nextpvr.com', 'nike': 'nike.com',
                'odampublishing': 'forum.odampublishing.com', 'odnoklassniki': 'ok.ru',
                'office365': 'office365.com', 'onlinesequencer': 'onlinesequencer.net', 'parler': 'parler.com',
                'patreon': 'patreon.com', 'pinterest': 'pinterest.com', 'plurk': 'plurk.com',
                'pornhub': 'pornhub.com', 'protonmail': 'protonmail.ch', 'quora': 'quora.com',
                'raidforums': 'raidforums.com', 'rambler': 'rambler.ru', 'redtube': 'redtube.com',
                'replit': 'replit.com', 'rocketreach': 'rocketreach.co', 'samsung': 'samsung.com',
                'seoclerks': 'seoclerks.com', 'sevencups': '7cups.com', 'smule': 'smule.com',
                'snapchat': 'snapchat.com', 'soundcloud': 'soundcloud.com', 'sporcle': 'sporcle.com',
                'spotify': 'spotify.com', 'strava': 'strava.com', 'taringa': 'taringa.net',
                'teamtreehouse': 'teamtreehouse.com', 'tellonym': 'tellonym.me', 'thecardboard': 'thecardboard.org',
                'therianguide': 'forums.therian-guide.com', 'thevapingforum': 'thevapingforum.com',
                'treasureclassifieds': 'forum.treasureclassifieds.com', 'tumblr': 'tumblr.com',
                'tunefind': 'tunefind.com', 'twitter': 'twitter.com', 'venmo': 'venmo.com', 'vivino': 'vivino.com',
                'voxmedia': 'voxmedia.com', 'vrbo': 'vrbo.com', 'vsco': 'vsco.co', 'wattpad': 'wattpad.com',
                'wordpress': 'wordpress.com', 'xing': 'xing.com', 'xnxx': 'xnxx.com', 'xvideos': 'xvideos.com',
                'yahoo': 'yahoo.com', 'hubspot': 'hubspot.com', 'pipedrive': 'pipedrive.com',
                'insightly': 'insightly.com', 'nutshell': 'nutshell.com', 'zoho': 'zoho.com',
                'axonaut': 'axonaut.com', 'amocrm': 'amocrm.com', 'nimble': 'nimble.com', 'nocrm': 'nocrm.io',
                'teamleader': 'teamleader.eu'}

        return_results = []
        return_results_queue = Queue()

        modules = holehe_core.import_submodules('holehe.modules')
        websites = []

        for module in modules:
            if len(module.split(".")) > 3:
                modu = modules[module]
                site = module.split(".")[-1]
                if parameters['Use Password Recovery Methods'] == 'No':
                    if "adobe" not in str(modu.__dict__[site]) and "mail_ru" not in str(
                            modu.__dict__[site]) and "odnoklassniki" not in str(modu.__dict__[site]):
                        websites.append(modu.__dict__[site])
                else:
                    websites.append(modu.__dict__[site])

        async def launch_module(websiteFuncToUse, emailToUse, clientToUse, outList):
            try:
                await websiteFuncToUse(emailToUse, clientToUse, outList)
            except Exception:
                name = str(websiteFuncToUse).split('<function ')[1].split(' ')[0]
                outList.append({"name": name, "domain": data[name],
                                "rateLimit": True,
                                "exists": False,
                                "emailrecovery": None,
                                "phoneNumber": None,
                                "others": None})

        async def parseEntities():
            for entity in entityJsonList:
                uid = entity['uid']
                email = entity['Email Address']

                client = httpx.AsyncClient(timeout=10)
                out = []
                futuresList = []
                for website in websites:
                    futuresList.append(launch_module(website, email, client, out))
                for futureObject in futuresList:
                    await futureObject
                await client.aclose()

                for potential_find in out:
                    if potential_find['rateLimit'] is False and potential_find['exists'] is True:
                        child_index = len(return_results)
                        return_results.append([{'Domain Name': potential_find['domain'],
                                                'Entity Type': 'Domain'},
                                               {uid: {'Resolution': 'Holehe Account Exists on Domain', 'Notes': ''}}])

                        found_email = potential_find['emailrecovery']
                        if found_email is not None:
                            return_results.append([{'Email Address': found_email,
                                                    'Entity Type': 'Email Address'},
                                                   {child_index: {'Resolution': 'Holehe Account Recovery Email',
                                                                  'Notes': ''}}])
                        found_phone_number = potential_find['phoneNumber']
                        if found_phone_number is not None:
                            return_results.append([{'Phone Number': found_phone_number,
                                                    'Entity Type': 'Phone Number'},
                                                   {child_index: {'Resolution': 'Holehe Account Phone Number',
                                                                  'Notes': ''}}])
                        if potential_find['others'] is not None:
                            if 'FullName' in str(potential_find['others'].keys()):
                                return_results.append([{'Phrase': potential_find['others']['FullName'],
                                                        'Entity Type': 'Phrase'},
                                                       {child_index: {'Resolution': 'Holehe Account Owner Name',
                                                                      'Notes': ''}}])
                            if 'Date, time of the creation' in str(potential_find['others'].keys()):
                                return_results.append([{'Date': potential_find['others']['Date, time of the creation'],
                                                        'Entity Type': 'Date'},
                                                       {child_index: {'Resolution': 'Holehe Account Creation Date',
                                                                      'Notes': ''}}])
                sleep(5)  # Safety measure to ensure we don't get locked out due to spamming.

        def processFunc(process_queue: Queue):
            import asyncio
            from concurrent.futures import ThreadPoolExecutor

            executor = ThreadPoolExecutor(15)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.set_default_executor(executor)
            loop.run_until_complete(parseEntities())
            loop.close()
            process_queue.put(return_results)

        p = Process(target=processFunc, args=(return_results_queue,))
        p.start()
        p.join()
        try:
            return_results = return_results_queue.get(timeout=1)
            return return_results
        except Empty:
            return "Error occurred when processing entities for Holehe module."
