"""
Given user,pw,link scrape all folder names in page

For all scraped data, search in winlogs, 

for each option, show closest found in db and query user for handling

"""
import sys, json, time
import selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import subprocess, shlex
from pathlib import Path
from configparser import ConfigParser
from bs4 import BeautifulSoup
from tabulate import tabulate
from difflib import get_close_matches

if len(sys.argv) < 2:
    print("No URL Given")
    exit(1)

TARGET_URL = sys.argv[1]

##################### DATABASE HANDLING ##############################
HEADERS = ["First", "Last", "Rating", "Social", "Have", "Size", "Files"]


def searchwins(data, **arguments):
    # searches from winlog db, returns Listof(Listof(info)) the variable res
    qry_fn = arguments["fn"].lower()
    qry_ln = arguments["ln"].lower() if "ln" in arguments else ""
    res = []
    for fn, listofentries in data.items():
        if fn.startswith(qry_fn):
            # if fn == qry_fn:
            if qry_ln:
                res += [
                    [
                        fn,
                        entry["lastname"],
                        entry["rating"],
                        entry["soc"],
                        entry["have"],
                        entry["size"],
                        entry["files"],
                    ]
                    for entry in listofentries
                    if qry_ln in entry["lastname"]
                ]
            else:
                res += [
                    [
                        fn,
                        entry["lastname"],
                        entry["rating"],
                        entry["soc"],
                        entry["have"],
                        entry["size"],
                        entry["files"],
                    ]
                    for entry in listofentries
                ]

    res = sorted(res)
    if res:
        # return them
        print("Found following potential matches: ")
        print(tabulate(res, headers=HEADERS))
    else:
        # empty res, look for top 5 most similar
        alt = get_close_matches(qry_fn, data.keys(), n=5, cutoff=0.6)
        print(f"Did you mean to look for: {alt}?")

    return res


def get_all_lastnames(fnentry, targetln):
    res = []
    for record in fnentry:
        if record["lastname"] == targetln:
            res += list(record.values())
    return [res]


def addwins(args, data, f):
    fn = args["fn"]
    ln = args["ln"]
    rt = args["rating"]
    soc = args["soc"]
    hv = args["have"]
    sz = ""
    fi = ""
    if fn in data:
        inrecord = get_all_lastnames(data[fn], ln)
        if inrecord[0]:
            print("This entry already exists")
            print(tabulate(inrecord, headers=HEADERS))
            return
        else:
            # add this last name record (empty case)
            data[fn].append(
                {
                    "lastname": ln,
                    "soc": soc,
                    "have": hv,
                    "rating": rt,
                    "size": sz,
                    "files": fi,
                }
            )
    else:
        data[fn] = [
            {
                "lastname": ln,
                "soc": soc,
                "have": hv,
                "rating": rt,
                "size": sz,
                "files": fi,
            }
        ]
    f.seek(0)
    f.write(json.dumps(data))
    f.truncate()
    print("Record added!")


def modifywins(data, f, arguments):
    fn = arguments["fn"]
    ln = arguments["ln"]
    rt = arguments["rating"]
    soc = arguments["soc"]
    hv = arguments["have"]
    sz = ""
    fi = ""
    new_ln = arguments["new_ln"]

    found = False

    if fn in data:
        if ln:
            target = None
            for entry in data[fn]:
                if entry["lastname"] == ln:
                    found = True
                    print("Original entry:")
                    print(
                        tabulate(
                            [
                                [
                                    fn,
                                    entry["lastname"],
                                    entry["rating"],
                                    entry["soc"],
                                    entry["have"],
                                    entry["size"],
                                    entry["files"],
                                ]
                            ],
                            headers=HEADERS,
                        )
                    )
                    entry["have"] = True if hv else False
                    if soc:
                        entry["soc"] = soc
                    if sz:
                        entry["size"] = sz
                    if fi:
                        entry["files"] = fi
                    if rt:
                        entry["rating"] = int(rt)
                    if new_ln:
                        entry["lastname"] = new_ln
                    break

            if found:
                print("Modified entry:")
                print(
                    tabulate(
                        [
                            [
                                fn,
                                entry["lastname"],
                                entry["rating"],
                                entry["soc"],
                                entry["have"],
                                entry["size"],
                                entry["files"],
                            ]
                        ],
                        headers=HEADERS,
                    )
                )
                f.seek(0)
                f.write(json.dumps(data))
                f.truncate()
            else:
                print(
                    "last name not found. pls search first name to get temporary last name, exiting"
                )
        else:
            print(
                "no last name given. pls search first name to get temporary last name, exiting"
            )
    else:
        print(f'no record with firstname "{fn}" found')


##################### APPLICATION ##############################


def go_back_to_main(driver):
    # TODO: from a specific folder, go back one
    bread_crumbs = driver.find_elements(By.CLASS_NAME, "fm-breadcrumbs")
    # go to prev
    bread_crumbs[-2].click()
    print(driver.current_url)


def scroll_until_see_and_click(driver, folder_name):
    # Find the row element using the specified text
    # first check
    row_element = []
    try:
        row_element = driver.find_element(
            By.XPATH, "//td[contains(., '" + folder_name + "')]"
        )
        if row_element.text != folder_name:
            row_element = []
            raise Exception
    except Exception as e:
        # if not, scroll and keep checking until so
        scrollable_div = driver.find_element(
            By.CSS_SELECTOR, "div.grid-scrolling-table"
        )
        scroll_amount = driver.execute_script(
            "return arguments[0].clientHeight;", scrollable_div
        )

        while not row_element:
            driver.execute_script(
                """return arguments[0].dispatchEvent(
                new WheelEvent('wheel', {
                    deltaX: 0,
                    deltaY: arguments[1],
                    deltaZ: 0,
                    deltaMode: WheelEvent.DOM_DELTA_PIXEL,
                    button: 1 // Middle mouse button
                })
            );""",
                scrollable_div,
                scroll_amount,
            )
            time.sleep(0.1)
            # try to find
            try:
                row_element = driver.find_element(
                    By.XPATH, "//td[contains(., '" + folder_name + "')]"
                )
                if row_element.text != folder_name:
                    row_element = []
                    raise Exception
            except:
                pass

    # click into new page
    driver.execute_script(
        "var event = new MouseEvent('dblclick', { 'view': window, 'bubbles': true, 'cancelable': true }); arguments[0].dispatchEvent(event);",
        row_element,
    )
    print(driver.current_url)


def handle_user_response(cur_entry, driver, login):
    triage = input(
        "Default:Pass ([enter]) --- Missing (N) --- Other (mod/man/s)\n"
    ).lower()
    if triage == "n":
        # scroll until see 'folder_name/cur_entry', double click
        scroll_until_see_and_click(driver, cur_entry)

        print("Adding new entry!\n")
        while True:
            try:
                arguments = {
                    "fn": input("First Name: ").lower(),
                    "ln": input("Last Name: ").lower(),
                    "rating": int(input("Rating: ")),
                    "have": bool(input("Have: ")),
                    "soc": input("Social: "),
                }
                if not any(x == "retry" for x in arguments.values()):
                    break
            except:
                pass
            print("Incorrect input, try again")

        with open("winlog.json", "r+") as wl:
            data = json.loads(wl.read())
            addwins(arguments, data, wl)

        # go back
        go_back_to_main(driver)

    elif triage == "mod":
        # modify an existing entry
        print("### leaving blank = old default value ###")
        arguments = {
            "fn": input("Old First Name: ").lower(),
            "ln": input("Old Last Name: ").lower(),
            "new_ln": input("New Last Name: ").lower(),
            "rating": input("Rating: "),
            "have": bool(input("Have: ")),
            "soc": input("Social: "),
        }
        with open("winlog.json", "r+") as wl:
            data = json.loads(wl.read())
            modifywins(data, wl, arguments)

    elif triage == "man":
        # manually perform operations (using popen)

        print("Entering manual mode, make sure you handle the current patient")
        while True:
            try:
                print(
                    "Type command to be passed to old api (q for stopping, h for help)"
                )
                cmd = input("Command: ")
                print("debug", cmd)
                if cmd:
                    if cmd == "q":
                        print("Exiting manual mode...")
                        break
                    elif cmd == "h":
                        print(
                            "s {fn} --ln={ln} --rating={lambda as a string e.g. '=>4'}"
                        )
                        print("a {--no-have} {fn} {ln} {rating} --soc={social}")
                        print(
                            "m {--no-have}=True {fn} {ln} --rating={rating} --soc={social}"
                        )
                        print("d {fn} {ln}")
                    elif cmd == "clear":
                        # pass it vanila to clear screen
                        run_command("clear")
                    else:
                        print(f"Running: python manager.py {cmd}\n")
                        rc = run_command(f"python manager.py {cmd}")
                        # print(rc)
            except:
                pass

    elif triage == "s":
        # skip and save to a file
        print("saving to skipped.txt")
        with open("skipped.txt", "a") as skpd:
            skpd.write(f"{cur_entry}\n")

        print("Saving/Skipping!")
    elif triage == "q":
        print("Exiting...")
        shut_down(driver, login)
    else:
        # Just Pass and ignore
        pass

    print("--------------------------------------------------")


def run_command(command):
    process = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
    while True:
        output = process.stdout.readline().decode()
        if output == "" and process.poll() is not None:
            break
        if output:
            print(output.strip())
    rc = process.poll()
    if command != "clear":
        print("\n\n--------------------------------------------------")
    return rc


def flush_screen():
    # Clear the screen
    sys.stdout.write("\033c")
    sys.stdout.flush()


def shut_down(driver, login):
    if login:
        driver.find_element(By.CLASS_NAME, "icon-side-menu").click()
        scrollable_side = driver.find_element(By.CLASS_NAME, "top-menu-scroll")
        driver.execute_script(
            """return arguments[0].dispatchEvent(
                new WheelEvent('wheel', {
                    deltaX: 0,
                    deltaY: arguments[1],
                    deltaZ: 0,
                    deltaMode: WheelEvent.DOM_DELTA_PIXEL,
                    button: 1 // Middle mouse button
                    }));""",
            scrollable_side,
            1000,
        )
        WebDriverWait(driver=driver, timeout=15).until(
            # EC.presence_of_element_located((By.CLASS_NAME, "logout"))
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button.mega-button.branded-red.logout")
            )
            # EC.element_to_be_clickable((By.CLASS_NAME, "logout"))
        )
        driver.find_element(
            By.CSS_SELECTOR, "button.mega-button.branded-red.logout"
        ).click()
    driver.quit()
    exit(0)


def get_creds(loc=Path.cwd() / ".credentials.ini"):
    config_f = ConfigParser()
    config_f.read(loc)
    return config_f.get("credentials", "username"), config_f.get(
        "credentials", "password"
    )


##################### SCRAPING PROCESS ##############################


# initialize the Chrome driver
def get_chrome_options():
    chrome_options = Options()
    # chrome_options.add_argument("--window-size=1920,1080")
    # chrome_options.add_argument("--start-maximized")
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return chrome_options


def get_fox_options():
    options = selenium.webdriver.firefox.options.Options()
    # options.add_argument("--window-size=1920,1080")
    # options.add_argument("--start-maximized")
    # options.add_argument("--headless")
    # options.add_argument("--disable-gpu")
    options.add_argument("no-sandbox")
    return options


def mega_login(driver, username, password):
    # head to mega login page
    driver.get("https://mega.nz/login")

    # wait for load
    WebDriverWait(driver=driver, timeout=15).until(
        EC.presence_of_element_located((By.ID, "login-name2"))
    )

    # find username/email field and send the username itself to the input field
    driver.find_element("id", "login-name2").send_keys(username)
    # find password input field and insert password as well
    driver.find_element("id", "login-password2").send_keys(password)
    # uncheck remember me
    driver.find_element("id", "login-check2").click()
    # click login button
    driver.find_element(By.CLASS_NAME, "login-button").click()

    # wait for load
    WebDriverWait(driver=driver, timeout=60).until(
        EC.presence_of_element_located((By.CLASS_NAME, "onboarding-control-panel"))
    )


def selenium_scrape(login=False, **kwargs):
    # returns html for BeautifulSoup
    # driver = webdriver.Chrome("chromedriver", options=get_options())
    driver = webdriver.Firefox(options=get_fox_options())
    if login:
        mega_login(driver, kwargs["usr"], kwargs["pwd"])
    driver.get(TARGET_URL)

    WebDriverWait(driver=driver, timeout=120).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "size"))
    )

    # show by list
    driver.find_element(By.CLASS_NAME, "icon-view-medium-list").click()

    # show by tile
    # driver.find_element(By.CLASS_NAME, "icon-view-grid").click()

    return driver


def scrape_page(driver, scraped_so_far_text):
    # returns newly scraped items as a list
    html = driver.page_source

    soup = BeautifulSoup(html, "lxml")

    return [
        item.text
        for item in soup.find_all("span", class_="tranfer-filetype-txt")
        if item.text not in scraped_so_far_text and item.text
    ]


def scroll_and_scrape(driver, items_scraped, scrollable, scroll_amount):
    # scroll
    driver.execute_script(
        """return arguments[0].dispatchEvent(
        new WheelEvent('wheel', {
            deltaX: 0,
            deltaY: arguments[1],
            deltaZ: 0,
            deltaMode: WheelEvent.DOM_DELTA_PIXEL,
            button: 1 // Middle mouse button
        })
    );""",
        scrollable,
        scroll_amount,
    )
    # slight wait
    time.sleep(0.1)
    # scrape
    return scrape_page(driver, items_scraped)


##################### MAIN ##############################


def main(login):
    usr, pwd = get_creds()
    driver = selenium_scrape(login, usr=usr, pwd=pwd)

    # Get initial height of the page
    scrollable_div = driver.find_element(By.CSS_SELECTOR, "div.grid-scrolling-table")
    scroll_height = driver.execute_script(
        "return arguments[0].scrollHeight;", scrollable_div
    )
    client_height = driver.execute_script(
        "return arguments[0].clientHeight;", scrollable_div
    )
    scroll_top = driver.execute_script("return arguments[0].scrollTop;", scrollable_div)
    scroll_amount = client_height
    # first scrape on page
    items_scraped = scrape_page(driver, [])
    while scroll_top + client_height < scroll_height:
        items_scraped += scroll_and_scrape(
            driver, items_scraped, scrollable_div, scroll_amount
        )
        scroll_top = driver.execute_script(
            "return arguments[0].scrollTop;", scrollable_div
        )

    # scroll back to top
    while scroll_top > 0:
        driver.execute_script(
            """return arguments[0].dispatchEvent(
            new WheelEvent('wheel', {
                deltaX: 0,
                deltaY: arguments[1],
                deltaZ: 0,
                deltaMode: WheelEvent.DOM_DELTA_PIXEL,
                button: 1 // Middle mouse button
            })
        );""",
            scrollable_div,
            -scroll_amount,
        )
        scroll_top = driver.execute_script(
            "return arguments[0].scrollTop;", scrollable_div
        )

    # search in local db
    for folder_name in items_scraped:
        print(f"Searching for `{folder_name}`")
        # splitfolder = folder_name.split()
        first_name = folder_name.split()[0].lower()

        # file context
        with open("winlog.json", "r+") as wl:
            data = json.loads(wl.read())

            # Only search by firstname
            res = searchwins(data, fn=first_name)

        handle_user_response(folder_name, driver, login)
        flush_screen()

    print("Thanks for using scraper!")

    with open("skipped.txt", "a") as skpd:
        skpd.write("--------------------------------------------------\n")

    shut_down(driver, login)


if __name__ == "__main__":
    login = bool(input("Login? (Empty=No): "))
    main(login)
