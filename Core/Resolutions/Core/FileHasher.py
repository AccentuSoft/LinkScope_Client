#!/usr/bin/env python3


class FileHasher:
    name = "Get File Hash"
    description = "Get the Hash of a file"
    originTypes = {"Image", "Document", "Video", "Archive", "Disk"}
    resultTypes = {'Hash'}
    parameters = {'hashing_algorithms': {'description': 'The type of hash/es that will be returned',
                                         'type': 'MultiChoice',
                                         'value': {'SHA1', 'SHA256', 'MD5'}
                                         }}

    def resolution(self, entityJsonList, parameters):
        import hashlib
        from pathlib import Path

        return_result = []
        hashing_algorithms = parameters['hashing_algorithms']
        for entity in entityJsonList:
            uid = entity['uid']
            file_path = Path(entity["File Path"])
            if not (file_path.exists() and file_path.is_file()):
                continue
            block_size = 65536  # The size of each read from the file
            for hashing_algorithm in hashing_algorithms:
                if hashing_algorithm == "SHA256":
                    file_hash = hashlib.sha256()  # nosec
                elif hashing_algorithm == "SHA1":
                    file_hash = hashlib.sha1()  # nosec
                else:
                    file_hash = hashlib.md5()  # nosec
                with open(file_path, 'rb') as f:
                    fb = f.read(block_size)
                    while len(fb) > 0:
                        file_hash.update(fb)
                        fb = f.read(block_size)
                resulting_hash = file_hash.hexdigest()
                return_result.append([{'Hash Value': resulting_hash,
                                       'Hash Algorithm': hashing_algorithm,
                                       'Entity Type': 'Hash'},
                                      {uid: {'Resolution': hashing_algorithm + ' Hash', 'Notes': ''}}])
        return return_result
