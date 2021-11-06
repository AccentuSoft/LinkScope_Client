#!/usr/bin/env python3


class ImageToDevice:
    name = "Device From Image"
    description = "Find information about on what device the image was taken"
    originTypes = {"Image"}
    resultTypes = {'Phrase'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        from exif import Image

        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            index_of_child = len(return_result)
            image_path = Path(entity["File Path"])
            if not (image_path.exists() and image_path.is_file()):
                continue
            with open(image_path, 'rb') as image_file:
                my_image = Image(image_file)
                if my_image.has_exif is False:
                    continue
                else:
                    for tag in my_image.list_all():
                        if tag == "make":
                            return_result.append([{'Phrase': my_image.make,
                                                   'Entity Type': 'Phrase'},
                                                  {uid: {'Resolution': 'ExifMetadata Device Manufacturer',
                                                         'Notes': ''}}])
                        if tag == "model":
                            return_result.append([{'Phrase': my_image.model,
                                                   'Entity Type': 'Phrase'},
                                                  {index_of_child: {'Resolution': 'ExifMetadata Device Model',
                                                                    'Notes': ''}}])
        return return_result
