#!/usr/bin/env python3


class OrgSearch_GitAllSecrets:
    # A string that is treated as the name of this resolution.
    name = "Git-All-Secrets OrgSearch"

    category = "Secrets & Leaks"

    # A string that describes this resolution.
    description = "Searches Github Organization repositories for exposed secrets. Requires Docker to be installed."

    originTypes = {'GitHub Organisation'}

    resultTypes = {'GitHub Organisation', 'GitHub Secret', 'GitHub Repository', 'GitHub FilePath', 'Hash',
                   'GitHub Branch'}

    parameters = {'Github Token': {'description': 'Github personal access token.\n'
                                                  'We need this because unauthenticated requests to the Github API '
                                                  'are likely to hit the rate limit.',
                                   'type': 'String',
                                   'value': '',
                                   'global': True},
                  }

    def resolution(self, entityJsonList, parameters):
        import docker
        import json
        import tempfile
        import re
        from pathlib import Path

        pattern = re.compile(r'\{(?:[^{}]|(?R))*\}')
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        returnResults = []

        for entity in entityJsonList:
            uid = entity['uid']
            hogSecret = []
            client = docker.from_env()
            with tempfile.TemporaryDirectory() as tempDir:
                tempPath = Path(tempDir).absolute()
                client.containers.run('abhartiya/tools_gitallsecrets:latest',
                                      f'-token={parameters["Token"]} '
                                      f'-org={entity[list(entity)[1]]} -output=/home/out.txt',
                                      volumes={str(tempPath): {'bind': '/home',
                                                               'mode': 'rw'}}, remove=True)
                jsonFile = tempPath / 'out.txt'
                if jsonFile.exists():
                    with open(jsonFile, 'r') as jsonFileHandler:
                        jsonContents = jsonFileHandler.read()
                    with open(jsonFile, 'r') as file:
                        hogSecret.extend(next(file) for line in file if "Commit" in line)
            repoSupervisor = jsonContents.split('Tool: repo-supervisor')[1]
            truffleHog = jsonContents.split('Tool: repo-supervisor')[0]
            orgOrUser = [
                line.split(' ')
                for line in repoSupervisor.splitlines()
                if line.startswith('OrgorUser')
            ]
            data = pattern.findall(repoSupervisor)
            for value in data:
                data.append(json.loads(value))

            for index, userOrg in enumerate(orgOrUser):
                index_of_child = len(returnResults)
                returnResults.append(
                    [{'Organisation Name': f'Org or User: {userOrg[1]}',
                      'Entity Type': 'GitHub Organisation'},
                     {uid: {'Resolution': 'Tool: repo-supervisor',
                            'Notes': ''}}
                     ]
                )

                child_of_child = len(returnResults)
                returnResults.append([{'Repository Name': userOrg[3],
                                       'Entity Type': 'GitHub Repository'},
                                      {index_of_child: {'Resolution': 'Repository of Organisation',
                                                        'Notes': ''}}])
                childOfChild = 0
                if userOrg[3] in truffleHog and userOrg[1] in truffleHog:
                    userContent = truffleHog.split(f'OrgorUser: {userOrg[1]} RepoName: {userOrg[3]}')[1]
                    hogIndex = 0
                    for line in userContent.splitlines():
                        line = line.strip()
                        if 'Reason' in line:
                            childOfChild = len(returnResults)
                            returnResults.append([{'Phrase': ansi_escape.sub('', line),
                                                   'Notes': ansi_escape.sub('', hogSecret[hogIndex]),
                                                   'Entity Type': 'Phrase'},
                                                  {index_of_child: {'Resolution': 'GitHub Secret',
                                                                    'Notes': ''}}])
                            hogIndex += 1
                        elif 'Hash' in line:
                            returnResults.append([{'Hash Value': ansi_escape.sub('', line),
                                                   'Entity Type': 'Hash'},
                                                  {childOfChild: {'Resolution': 'Tool: truffleHog',
                                                                  'Notes': ''}}])
                        elif 'Filepath' in line:
                            returnResults.append([{'Filepath': ansi_escape.sub('', line),
                                                   'Entity Type': 'GitHub FilePath'},
                                                  {childOfChild: {'Resolution': 'GitHub FilePath',
                                                                  'Notes': ''}}])
                        elif 'Branch' in line:
                            returnResults.append([{'Branch': ansi_escape.sub('', line),
                                                   'Entity Type': 'GitHub Branch'},
                                                  {childOfChild: {'Resolution': 'GitHub Branch',
                                                                  'Notes': ''}}])

                for result in data:
                    for secret in result['result']:
                        secrets = (secret.get('secrets'))
                        if userOrg[3] in secret.get('filepath'):
                            child_child = len(returnResults)
                            returnResults.append([{'Filepath': secret.get('filepath'),
                                                   'Entity Type': 'GitHub FilePath'},
                                                  {child_of_child: {'Resolution': 'GitHub FilePath',
                                                                    'Notes': ''}}])

                            returnResults.extend(
                                [{'Secret': scrt,
                                  'Entity Type': 'GitHub Secret'},
                                 {child_child: {'Resolution': 'GitHub Secret',
                                                'Notes': ''}}
                                 ]
                                for scrt in secrets
                            )
        return returnResults
