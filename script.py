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

MESSAGES_TO_SEND = 500  # how many messages should be send in one sendout
REPEAT = 1  # how many times repeat sendout
REPEAT_PAUSE = 30  # how long in seconds should script wait before repeating sendout
UPDATE_TARGET_USERS = True  # update list of target users for every sendout
OFFSET_FOR_TARGETS = 0  # how many targets should script skip before start adding to targets list
FROM_END = False  # collect targets from end of conversations

SEND_MESSAGES_AFTER_UNREAD = True  # send messages to conversations where there are unread message by user

TOKENS = [
    "TOKEN_HERE"
]

PROXIES = [
    {}
]

ONE_SENDOUT_SIZE = 50  # amount of sent messages for one request to API

DEBUG = False


################################################################################


if os.path.exists("configuration.py"):
    from configuration import *

if not os.path.exists("data"):
    os.makedirs("data")

if not os.path.exists("proxies.txt"):
    with open("proxies.txt", "w") as o:
        o.write("")


################################## CONSTANTS  ##################################


API_URL = "https://api.vk.com/method/{{method}}?access_token={{token}}&v={version}".format(
    version="5.80"
)

FILTER = "unread" if SEND_MESSAGES_AFTER_UNREAD else "all"


################################## UTILITIES  ##################################


def raw_request(url, proxy={}, **params):
    data = urllib_parse.urlencode(params).encode()
    req = urllib_request.Request(url, data=data)

    if proxy:
        chosen_proxy_address = dict(**proxy)
    else:
        if PROXIES:
            chosen_proxy_address = choice(PROXIES)
        else:
            chosen_proxy_address = {}

    if DEBUG:
        print("\n-> {} | {}\n".format(url, chosen_proxy_address))

    proxy_support = urllib_request.ProxyHandler(chosen_proxy_address)
    opener = urllib_request.build_opener(proxy_support)
    urllib_request.install_opener(opener)

    try:
        with urllib_request.urlopen(req, timeout=2 if PROXIE_CHECKER else 20) as resp:
            if resp.getcode() != 200:
                return ""

            return resp.read().decode("utf-8")

    except Exception as e:
        try:
            PROXIES.remove(chosen_proxy_address)
        except ValueError:
            pass

        print(type(e), e)

        return ""

        return raw_request(url, proxy={}, **params)


def request(method, on_error=None, **params):
    vk_answer = raw_request(
        API_URL.format(
            method=method,
            token=choice(TOKENS)
        ),
        **params
    )

    if len(PROXIES) < 2:
        time.sleep(0.05)
    elif len(PROXIES) < 3:
        time.sleep(0.025)
    elif len(PROXIES) < 4:
        time.sleep(0.01)

    try:
        jsoned = json.loads(vk_answer)

        if not jsoned or "response" not in jsoned:
            raise ValueError

        if "error" in jsoned:
            print("\nerr", method, jsoned["error"])
    except json.JSONDecodeError:
        if on_error:
            return on_error(vk_answer, jsoned=False)

        return None

    except ValueError:
        if on_error:
            return on_error(vk_answer, jsoned=True)

        return None

    return jsoned["response"]


def chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i : i + n]


def clear_and_paste(msg, end=""):
    print("\r" + " " * 80 + "\r" + msg, end=end)


#################################### SCRIPT ####################################

def collect_target_peers(append=False):
    unanswered_peers = set()

    def add_to_unanswered_peers(answer):
        if not answer:
            return

        if FROM_END:
            working_items = answer["items"][::-1]
        else:
            working_items = answer["items"]

        for item in working_items:
            conversation = item["conversation"]
            last_message = item["last_message"]

            if not conversation["can_write"]["allowed"]:
                continue

            if FILTER == "unread" and \
                    last_message["from_id"] != last_message["peer_id"]:
                continue

            peer = conversation["peer"]

            unanswered_peers.add((peer["id"], peer["type"], peer["local_id"]))

            if len(unanswered_peers) >= MESSAGES_TO_SEND:
                return True

        return False

    for i in range(5):  # retries
        conversations = request(
            "messages.getConversations",
            filter=FILTER,
            offset=0,
            count=200,
        )

        if conversations:
            break

    count = conversations["count"]

    def micro_log(i):
        clear_and_paste(
            "Reading conversations: {}/{} | Collected {}/{}".format(
                i,
                count,
                len(unanswered_peers),
                MESSAGES_TO_SEND
            )
        )

    last_offset = 0

    if FROM_END:
        working_range = range(count - OFFSET_FOR_TARGETS - 200, -200, -200)
    else:
        working_range = range(OFFSET_FOR_TARGETS, count, 200)

    killed = False

    try:
        for i in working_range:
            if i < 0:
                i = 0

            micro_log(i)

            vk_answer = request(
                "messages.getConversations",
                filter=FILTER,
                offset=i,
                count=200,
            )

            last_offset = i

            if add_to_unanswered_peers(vk_answer):
                break
    except KeyboardInterrupt:
        killed = True

    clear_and_paste("Done reading conversations ({}).".format(
        len(unanswered_peers)
    ), end="\n")

    print("Last offset: {}".format(count - last_offset if FROM_END else last_offset))

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

    if killed:
        exit()


def validate_proxy_address(proxy_address):
    if not proxy_address:
        return (0, 0)

    http_response = ""  # http_response = raw_request("http://httpbin.org/post", proxy={"http": "http://" + proxy_address})
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
        pool = Pool(1 + os.cpu_count() * 10)
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
        local_ids = list(set(json.load(o)))

    new_local_ids = []

    def save_new_local_ids():
        with open("data/unanswered_peers_local_ids.json", "w") as o:
            json.dump(new_local_ids, o)

    local_ids_chunks = list(chunks(local_ids, ONE_SENDOUT_SIZE))
    chunks_amount = len(local_ids_chunks)

    print("=" * 30 + " Sending message: " + "=" * 30 + "\n" + MESSAGE + "\n" + "=" * 78)

    try:
        for i, chunk in enumerate(local_ids_chunks):
            ready_chunk = ",".join(str(local_id) for local_id in chunk)

            clear_and_paste(
                "Sending messages {}/{}".format(
                    i * ONE_SENDOUT_SIZE,
                    chunks_amount * ONE_SENDOUT_SIZE
                )
            )

            result = request(
                "messages.send",
                user_ids=ready_chunk,
                message=MESSAGE,
                attachment=ATTACHMENT,
                on_error=lambda answ, jsoned: [] if jsoned else None
            )

            if isinstance(result, (list, tuple)):
                for cresult in result:
                    if not cresult.get("peer_id", None):
                        continue

                    if cresult.get("error", None) and not cresult.get("message_id", None):
                        new_local_ids.append(cresult["peer_id"])

    except KeyboardInterrupt:
        for chunk in local_ids_chunks[i:]:
            for local_id in chunk:
                new_local_ids.append(local_id)

        save_new_local_ids()
        exit()

    finally:
        save_new_local_ids()

    clear_and_paste("Done sending messages ({}).".format(
        chunks_amount * ONE_SENDOUT_SIZE
    ), end="\n")


if __name__ == "__main__":
    import sys

    if "proxies" in sys.argv[1:]:
        PROXIE_CHECKER = True
        collect_and_validate_proxies()
        exit()

    else:
        PROXIE_CHECKER = False

    collect_proxies()

    if "keep" not in sys.argv[1:]:
        collect_target_peers()

    if "nosend" in sys.argv[1:]:
        exit()

    for _ in range(REPEAT - 1):
        perform_sendout()

        print("Sleeping for {} seconds...".format(REPEAT_PAUSE))
        time.sleep(REPEAT_PAUSE)

        if UPDATE_TARGET_USERS:
            collect_target_peers(append=True)

    perform_sendout()
