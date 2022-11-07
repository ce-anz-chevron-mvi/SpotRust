#!/usr/bin/python

## 
# A script to call Maximo Visual Inspection's model endpoint to segment rust areas on an image
# the script does two things: uploads image to an MVI instance for segmentation, receives the annotation and cleans it up:
# any polygons that are less than 64x64px in size are discarded, all polygons that start or end beyond image borders are discarded (MVI bug?)
# Arguments:
# argv[1] = MVI model API endpoint
# argv[2] = jpeg file to process
#
# questions and patches - mikhail.nikitin1@ibm.com
##

import os
import sys
import imantics
import requests
from PIL import Image
import urllib3, json


# get the base directory
if len(sys.argv) == 3:
    mvi_api_endpoint = sys.argv[1]
    source_file = sys.argv[2]
else:
    print('Please provide 2 arguments: '+ sys.argv[0] + ' <MVI model API endpoint> <file to process>')
    exit(1)

if os.path.isfile(source_file):
  orig_x, orig_y = Image.open(source_file).size
  
  headers = {
    'Content-Type':'multipart/form-data', 
    'Accept-Encoding': 'deflate, gzip, br',
    'filename' : os.path.basename(source_file),
    'Accept':'application/json'
  }
  # make a request and handle errors
  try:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.post(mvi_api_endpoint, files = {'files': open(source_file, "rb")}, timeout=60, verify=False)
    response.raise_for_status()
    # Code here will only run if the request is successful

    data = json.loads(response.text)

    # model generates multiple polygons so we'll check if:
    # 1. bounding box is smaller than 64x64 px
    # 2. size of any dimension or starting point goes beyond the original image dimension (MVI bug)
    # -- and we discard those

    im = imantics.Image.from_path(os.path.abspath(source_file))

    for polygon in data['classified']:
      if polygon['label'] == "Corrosion":
        poly = imantics.Polygons(polygon['polygons'])
        bbox = poly.bbox()
        
        if (bbox.height <= orig_y) & (bbox.width <= orig_x) & ((bbox.height >= 64) | (bbox.width >= 64)):
          im.add(imantics.Polygons(poly), category=imantics.Category("Corrosion"))

    coco_json = im.export(style='coco')
    im.save(os.path.dirname(source_file) + '/'+ os.path.basename(source_file) +'.json', style='coco')

  except requests.exceptions.HTTPError as errh:
    print(errh)
  except requests.exceptions.ConnectionError as errc:
    print(errc)
  except requests.exceptions.Timeout as errt:
    print(errt)
  except requests.exceptions.RequestException as err:
    print(err)

else:
  print ('Not a good file: '+ source_file)


