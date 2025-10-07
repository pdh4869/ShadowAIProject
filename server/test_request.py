import requests

url = "http://127.0.0.1:9123/mask-files/"
files = {"Files": open(r"C:\Users\USER\Desktop\test.docx", "rb")}
res = requests.post(url, files=files)
print(res.status_code)
print(res.json())
