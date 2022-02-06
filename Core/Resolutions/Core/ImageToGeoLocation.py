#!/usr/bin/env python3


class ImageToGeoLocation:
    name = "Geolocation From Image"
    description = "Find information about where an image was taken."
    originTypes = {"Image"}
    resultTypes = {'GeoCoordinates'}
    parameters = {}

    def resolution(self, entityJsonList, parameters):
        from pathlib import Path
        from exif import Image

        return_result = []
        for entity in entityJsonList:
            uid = entity['uid']
            image_path = Path(parameters['Project Files Directory']) / entity['File Path']
            if not (image_path.exists() and image_path.is_file()):
                continue
            with open(image_path, 'rb') as image_file:
                my_image = Image(image_file)
                if my_image.has_exif is False:
                    continue
                else:
                    for tag in my_image.list_all():
                        if tag == "gps_latitude":
                            return_result.append([{'Label': "Location of"+str(entity[list(entity)[1]].strip()),
                                                   'Latitude': my_image.gps_latitude,
                                                   'Longitude': my_image.gps_longitude,
                                                   'Entity Type': 'GeoCoordinates'},
                                                  {uid: {'Resolution': 'GeoCoordinates', 'Notes': ''}}])
        return return_result
