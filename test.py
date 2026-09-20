"""from asyncio import run
from classeviva import *

run(Utente("S13609293I", "w3Pietro-Pmzb#mpAJ&#").agenda())"""

"""
Host: web.spaggiari.eu
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0
Accept: */*
Accept-Language: en,it-IT;q=0.9
Accept-Encoding: gzip, deflate, br, zstd
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
X-Requested-With: XMLHttpRequest
Content-Length: 49
Origin: https://web.spaggiari.eu
Alt-Used: web.spaggiari.eu
Connection: keep-alive
Referer: https://web.spaggiari.eu/home/app/default/login.php?target=&mode=
Cookie: webrole=gen; webidentity=S13609293I; i18n_redirected=en; PHPSESSID=p4semi6f9hah1b4akhatu3c620jc4k0c; cookie_consent=3
Sec-Fetch-Dest: empty
Sec-Fetch-Mode: cors
Sec-Fetch-Site: same-origin
Priority: u=0
"""

"""headers = {
    "User-Agent": "CVVS/std/4.2.3 Android/12", # I have also tired the same exact agent
    "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
    "Accept": "*/*",
    "Accept-Language": "en,it-IT;q=0.9",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "content-type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
    #"Content-Length": "49",
    "Origin": "https://web.spaggiari.eu",
    "Alt-Used": "web.spaggiari.eu",
    "Connection": "keep-alive",
    "Referer": "https://web.spaggiari.eu/home/app/default/login.php?target=&mode=",
    #"Cookie": "webrole=gen; webidentity=S13609293I; i18n_redirected=en; PHPSESSID=p4semi6f9hah1b4akhatu3c620jc4k0c; cookie_consent=3",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=4",
}"""

import requests

LOGIN_PAGE = "https://web.spaggiari.eu/home/app/default/login.php?target=&mode="
AUTH_URL = "https://web.spaggiari.eu/auth-p7/app/default/AuthApi4.php?a=aLoginPwd"

session = requests.Session()

session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:156.0) Gecko/20100101 Firefox/156.0",
    "Accept": "*/*",
    "Accept-Language": "en,it-IT;q=0.9",
})

# 1. Establish a fresh server-side PHP session.
response = session.get(LOGIN_PAGE)
response.raise_for_status()

print("Cookies after login page:")
for cookie in session.cookies:
    print(cookie.name, "=", cookie.value)

# 2. Authenticate using THAT SAME requests.Session().
response = session.post(
    AUTH_URL,
    data={
        "cid": "",
        "uid": "S13609293I",
        "pwd": "e!HmK7t6.nHY",
        "pin": "",
        "target": "",
    },
    headers={
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://web.spaggiari.eu",
        "Referer": LOGIN_PAGE,
    },
)

print(response.status_code)
print(response.text)

print("\nCookies after authentication:")
for cookie in session.cookies:
    print(cookie.name, "=", cookie.value)