import requests, os
from PIL import Image, ImageDraw

# Ensure test image exists
img_path = 'test_image.png'
if not os.path.exists(img_path):
    img = Image.new('RGB', (600, 300), color='white')
    ImageDraw.Draw(img).text((10, 10), 'TEST', fill='black')
    img.save(img_path)

url = 'http://127.0.0.1:5001/api/v1/ocr'
with open(img_path, 'rb') as f:
    files = {'file': f}
    try:
        resp = requests.post(url, files=files, timeout=20)
        print('Status code:', resp.status_code)
        print('Response:', resp.text)
    except Exception as e:
        print('Request error:', e)
