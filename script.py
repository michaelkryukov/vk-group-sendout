from urllib import parse as urllib_parse, request as urllib_request, error as urllib_error
from multiprocessing import Pool
from random import choice
import json
import time
import math
import os


################################### SETTINGS ###################################


MESSAGE = "Привет. Проверка скрипта для рассылки.\nЯ поспамлю, соре ;)"  # \n is a newline, \\ is \ e.t.c.
ATTACHMENT = "photo-145935681_456239429"  # see https://vk.com/dev/messages.send field `attachment`

MINIMUM_MESSAGES_TO_SEND = 500  # how many messages should be send in one sendout
REPEAT = 1  # how many times repeat sendout
REPEAT_PAUSE = 30  # how long in seconds should script wait before repeating sendout
UPDATE_TARGET_USERS = True  # update list of target users for every sendout
OFFSET_FOR_TARGETS = 0  # how many targets should script skip before start adding to targets list

SEND_MESSAGES_AFTER_UNREAD = True  # send messages to conversations where there are unread message by user

TOKENS = [
    "TOKEN_HERE"
]

PROXIES = [
    {}
]

ONE_SENDOUT_SIZE = 50  # amount of sent messages for one request to API


################################################################################


if os.path.exists("configuration.py"):
    from configuration import *

if not os.path.exists("data"):
    os.makedirs("data")


################################## CONSTANTS  ##################################


API_URL = "https://api.vk.com/method/{{method}}?access_token={{token}}&v={version}".format(
    version="5.80"
)

FILTER = "unread" if SEND_MESSAGES_AFTER_UNREAD else "all"


################################## UTILITIES  ##################################


def raw_request(url, proxy={}, retry=4, **params):
    data = urllib_parse.urlencode(params).encode()
    req = urllib_request.Request(url, data=data)

    chosen_proxy_address = choice(PROXIES)

    proxy_support = urllib_request.ProxyHandler(chosen_proxy_address if not proxy else proxy)
    opener = urllib_request.build_opener(proxy_support)
    urllib_request.install_opener(opener)

    try:
        with urllib_request.urlopen(req, timeout=4) as resp:
            if resp.getcode() != 200:
                return ""

            return resp.read().decode("utf-8")

    except Exception:
        if not proxy:
            PROXIES.remove(chosen_proxy_address)

        if retry < 1:
            return ""

        time.sleep(0.1)

        return raw_request(url, proxy, retry - 1, **params)


def request(method, on_error=None, **params):
    vk_answer = raw_request(
        API_URL.format(
            method=method,
            token=choice(TOKENS)
        ),
        **params
    )

    time.sleep(0.1)

    try:
        jsoned = json.loads(vk_answer)

        if not jsoned or "error" in jsoned or "response" not in jsoned:
            raise ValueError

    except json.JSONDecodeError:
        if on_error:
            on_error(vk_answer, jsoned=False)

        return None

    except ValueError:
        if on_error:
            on_error(vk_answer, jsoned=True)

        return None

    return jsoned["response"]


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def clear_and_paste(msg, end=""):
    print("\r" + " " * 80 + "\r" + msg, end=end)


#################################### SCRIPT ####################################

def collect_unanswered_peers(append=False):
    unanswered_peers = set()

    def add_to_unanswered_peers(answer):
        for item in answer["items"]:
            conversation = item["conversation"]
            last_message = item["last_message"]

            if not conversation["can_write"]["allowed"]:
                continue

            if FILTER == "unread" and \
                    last_message["from_id"] != last_message["peer_id"]:
                continue

            peer = conversation["peer"]

            unanswered_peers.add((peer["id"], peer["type"], peer["local_id"]))

    offset = OFFSET_FOR_TARGETS

    conversations = request(
        "messages.getConversations",
        filter=FILTER,
        offset=offset,
        count=200,
    )
    count = conversations["count"]

    clear_and_paste("Reading conversations... {}/{}".format(0, count))
    add_to_unanswered_peers(conversations)

    for i in range(200, count - offset, 200):
        clear_and_paste("Reading conversations... {}/{}".format(i, count))

        add_to_unanswered_peers(
            request(
                "messages.getConversations",
                filter=FILTER,
                offset=offset + i,
                count=200,
            )
        )

    clear_and_paste("Done reading conversations ({}).".format(
        len(unanswered_peers)
    ), end="\n")

    local_ids = set()

    for peer in list(unanswered_peers):
        local_ids.add(peer[2])

    if append:
        with open("data/unanswered_peers_local_ids.json") as o:
            old_local_ids = json.load(o)

        for local_id in old_local_ids:
            local_ids.add(local_id)

    with open("data/unanswered_peers_local_ids.json", "w") as o:
        json.dump(list(local_ids), o)


def validate_proxy_address(proxy_address):
    http_response = raw_request("http://httpbin.org/post", proxy={"http": "http://" + proxy_address})
    https_response = raw_request("https://httpbin.org/post", proxy={"https": "https://" + proxy_address})

    return (
        1 if "http://httpbin.org/post" in http_response else 0,
        1 if "https://httpbin.org/post" in https_response else 0
    )


def validate_proxy_address_and_write(proxy_address):
    http_ok, https_ok = validate_proxy_address(proxy_address)

    if not https_ok:
        return

    with open("proxies.txt", "a") as o:
        o.write(proxy_address + "\n")


def collect_and_validate_proxies():
    proxies = set()

    clear_and_paste("Loading raw proxies...")

    with open("raw_proxies.txt") as o:
        for line in o:
            proxies.add(line.strip())

    try:
        pool = Pool(1 + os.cpu_count() * 20)
        pool.map(validate_proxy_address_and_write, proxies)
        pool.close()
        pool.join()
    except KeyboardInterrupt:
        pass

    nice_proxies = set()

    with open("proxies.txt") as o:
        for line in o:
            nice_proxies.add(line.strip())

    with open("proxies.txt", "w") as o:
        for proxy in nice_proxies:
            if ":" not in proxy:
                continue

            o.write(proxy + "\n")

    clear_and_paste("Loaded and validated {} proxies.".format(len(proxies)), end="\n")
    clear_and_paste("Loaded {} nice proxies.".format(len(nice_proxies)), end="\n")


def collect_proxies():
    nice_proxies = set()

    with open("proxies.txt") as o:
        for line in o:
            nice_proxies.add(line.strip())

    for nice_proxy in nice_proxies:
        PROXIES.append(
            {"https": nice_proxy}
        )


def perform_sendout():
    with open("data/unanswered_peers_local_ids.json", "r") as o:
        local_ids = json.load(o)

    new_local_ids = []

    def save_new_local_ids():
        with open("data/unanswered_peers_local_ids.json", "w") as o:
            json.dump(new_local_ids, o)

    local_ids_chunks = list(chunks(local_ids, ONE_SENDOUT_SIZE))
    chunks_amount = len(local_ids_chunks)

    print("=" * 30 + " Sending message: " + "=" * 30 + "\n" + MESSAGE + "\n" + "=" * 78)

    for i, chunk in enumerate(local_ids_chunks):
        if i % 10:
            save_new_local_ids()

        if i * ONE_SENDOUT_SIZE > MINIMUM_MESSAGES_TO_SEND:
            for local_id in chunk:
                new_local_ids.append(local_id)

            continue

        ready_chunk = ",".join(str(local_id) for local_id in chunk)

        clear_and_paste(
            "Sending messages... {}/{}".format(
                i * ONE_SENDOUT_SIZE,
                chunks_amount * ONE_SENDOUT_SIZE
            )
        )

        result = request(
            "messages.send",
            user_ids=ready_chunk,
            message=MESSAGE,
            attachment=ATTACHMENT
        )

        if not result:
            for local_id in chunk:
                new_local_ids.append(local_id)

        clear_and_paste(
            "Sleeping for {} seconds... {}/{}".format(
                0.1,
                i * ONE_SENDOUT_SIZE + ONE_SENDOUT_SIZE,
                chunks_amount * ONE_SENDOUT_SIZE
            )
        )

        time.sleep(0.1)

    save_new_local_ids()

    clear_and_paste("Done sending messages ({}).".format(
        chunks_amount * ONE_SENDOUT_SIZE
    ), end="\n")


if __name__ == "__main__":
    import sys

    if "proxies" in sys.argv[1:]:
        collect_and_validate_proxies()
        exit()

    collect_proxies()

    if "keep" not in sys.argv[1:]:
        collect_unanswered_peers()

    if "nosend" in sys.argv[1:]:
        exit()

    for _ in range(REPEAT - 1):
        perform_sendout()

        print("Sleeping for {} seconds...".format(REPEAT_PAUSE))
        time.sleep(REPEAT_PAUSE)

        if UPDATE_TARGET_USERS:
            collect_unanswered_peers(append=True)

    perform_sendout()
