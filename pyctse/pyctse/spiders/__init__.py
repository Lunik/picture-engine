# This package will contain the spiders of your Scrapy project
#
# Please refer to the documentation for information on how to create and manage
# your spiders.

import os
import base64
import hashlib
import json
from urllib.parse import urlparse

import scrapy
import cv2
import numpy

class ImageSpider(scrapy.Spider):
  name = "img"

  urls = [
    "https://www.google.com/search?q=face&tbm=isch",
    "https://reddit.com",
    "https://www.facebook.com",
    "https://www.instagram.com",
    "https://www.pinterest.com",
    "https://www.tumblr.com",
    "https://www.flickr.com",
    "https://www.twitter.com",
    "https://www.linkedin.com",
    "https://www.youtube.com",
    "https://www.skyrock.com/blog/",
  ]

  def start_requests(self):
    for url in self.urls:
      yield scrapy.Request(url, meta={'playwright': True})

  def parse(self, response):
    # Get all the image links
    images = response.css("img::attr(src)").extract()
    # Save all the images in the folder
    for image in images:
      image_url = urlparse(image)
      # Handle image with base64 data inline
      if image_url.scheme == "data":
        yield self.process_image(response.url, base64.b64decode(image.split(",")[1]))
      else:
        if image_url.scheme == "":
          image_url = image_url._replace(scheme="https")
        yield scrapy.Request(response.urljoin(image_url.geturl()), callback=self.handle_image)

    # Follow all the links
    for link in response.css("a::attr(href)").extract():
      link_url = urlparse(link)
      if link_url.scheme == "":
        link_url = link_url._replace(scheme="https")

        if link_url.path.endswith(".png") or link_url.path.endswith(".jpg") or link_url.path.endswith(".jpeg") or link_url.path.endswith(".gif") or link_url.path.endswith(".svg"):
          yield scrapy.Request(response.urljoin(link_url.geturl()), callback=self.handle_image)
        else:
          yield response.follow(response.urljoin(link_url.geturl()), callback=self.parse, meta={'playwright': True})

  def handle_image(self, response):
    # Parse the content type
    content_type = response.headers["Content-Type"].decode().split("/")[-1]
    content_type = content_type.split("+")[0]
    # Save the image
    self.process_image(response.url, response.body, content_type)

  def process_image(self, url, content, content_type="webp"):
    if content_type not in ["png", "jpg", "jpeg", "webp", "gif", "svg"]:
      print(f"Ignored content type: {content_type}")
      return
    
    # Find face in the image (content) and save it
    image = numpy.fromstring(content, numpy.uint8)
    gray = cv2.imdecode(image, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(
      gray,
      scaleFactor=1.1,
      minNeighbors=5,
      minSize=(30, 30),
    )

    print(f"Found {len(faces)} face(s) in {url}")
    if len(faces) == 0:
      return

    for (x, y, w, h) in faces:
      cv2.rectangle(gray, (x, y), (x+w, y+h), (0, 255, 0), 2)

    # Extract the domain name
    domain = url.split("/")[2]
    # Extract the file name
    file_name = hashlib.md5(url.encode()).hexdigest()
    # Save the image
    file_path = f"result/{domain}/{file_name}.{content_type}"

    # Create the folder if it doesn't exist
    if not os.path.exists(os.path.dirname(file_path)):
      os.makedirs(os.path.dirname(file_path))

    # Save the image
    cv2.imwrite(file_path, gray)
    with open(f"{file_path}.metadata.json", "w") as f:
      f.write(json.dumps({
        "url": url,
        "faces_count": len(faces),
        "faces": faces.tolist(),
      }, indent=2))
