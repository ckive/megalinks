"""
fn null or str
ln: null or str
soc: null or str
files:  null or int
pics/vids: null OR (pics,vids)
size:   in MBs
rating  (4,5 are collectable, 5 are fpb)
have: T/F

4 Modes
    - search [firstname] [lastname(opt)] [have(opt)] [rating(opt)]
    - add [firstname] [lastname(opt)] [have] [rating] 
        --optionals: --soc=ins --size=mb --files=(pics,vids)
    - modify [firstname] [lastname]
        --optionals: --have=T/F --rating=T/F --soc=ins --size=mb --files=(pics,vids)
    - delete [firstname] [lastname]

data in the form
{
    "firstname": [
        {
            "lastname": str/strofnum
            "soc": str
            "have": T/F
            "rating": int
            "size": None/float
            "files": tuple(int,int)
        }
    ]
}
"""
import json, sys, argparse, os
from difflib import *
from tabulate import tabulate

HEADERS = ["First", "Last", "Rating", "Social", "Have", "Size", "Files"]


def searchwins(args, data, f=None):
    res = []
    for fn, listofentries in data.items():
        if fn.startswith(args.firstname):
            if args.ln:
                # res += [[fn,entry['lastname'],entry['rating'],entry['soc'],entry['have'],entry['size'],entry['files']] for entry in listofentries if entry['lastname'].startswith(args.lastname)]
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
                    if args.ln in entry["lastname"]
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
    # deal with options
    if args.rating:
        lamda = lambda x: eval("x" + args.rating)
        res = [
            [fn, ln, rt, soc, hv, sz, fi]
            for fn, ln, rt, soc, hv, sz, fi in res
            if lamda(rt)
        ]
    have = "True" == args.have
    print(have)
    if args.have:
        res = [
            [fn, ln, rt, soc, hv, sz, fi]
            for fn, ln, rt, soc, hv, sz, fi in res
            if hv == have
        ]

    if res:
        # return them
        print(tabulate(sorted(res), headers=HEADERS))

    else:
        # empty res, look for top 5 most similar
        alt = get_close_matches(args.firstname, data.keys(), n=5, cutoff=0.6)
        print(f"did you mean to look for {alt}?")


def get_all_lastnames(fnentry, targetln):
    res = []
    for record in fnentry:
        if record["lastname"] == targetln:
            res += list(record.values())
    return [res]


def addwins(args, data, f):
    fn = args.firstname.lower()
    ln = args.lastname.lower()
    rt = args.rating
    soc = args.soc
    hv = args.have
    sz = args.size
    fi = args.files
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
                    "lastname": str(len(data[fn])) if ln == "" else ln,
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
                "lastname": "0" if ln == "" else ln,
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
    print("record added")


def modifywins(args, data, f):
    print("reached modify")
    fn = args.firstname.lower()
    ln = args.lastname.lower()
    rt = args.rating
    soc = args.soc
    hv = args.have
    sz = args.size
    fi = args.files
    new_ln = args.ln
    new_fn = args.fn
    found = False
    if new_fn:
        print("first name change must be manual, exiting")
        return
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
                        entry["rating"] = rt
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


def deletewins(args, data, f):
    fn = args.firstname.lower()
    ln = args.lastname.lower()
    if fn in data:
        lnames = [e["lastname"] for e in data[fn]]
        if ln not in lnames:
            print("Entry not found")
            return
        else:
            # delete it (check if last)
            if len(lnames) > 1:
                for i in range(len(data[fn])):
                    if data[fn][i]["lastname"] == ln:
                        break
                data[fn].pop(i)
            else:
                # last one here
                del data[fn]
            print(f"Deleted {fn} {ln}")
    else:
        print("First name not found")

    f.seek(0)
    f.write(json.dumps(data))
    f.truncate()


def main():
    # top level parser
    parser = argparse.ArgumentParser()
    action = parser.add_subparsers(required=True)

    # search subparser
    search = action.add_parser("search", aliases=["s"])
    search.add_argument("firstname", type=str)
    search.add_argument("--ln", type=str)
    search.add_argument("--have")
    search.add_argument("--rating")
    search.set_defaults(func=searchwins)

    # add new entries to log
    add = action.add_parser("add", aliases=["a"])
    add.add_argument("firstname", type=str)
    add.add_argument("lastname", type=str)
    add.add_argument("--have", default=True, action=argparse.BooleanOptionalAction)
    add.add_argument("rating", type=int)
    add.add_argument("--soc")
    add.add_argument("--size", type=float)
    add.add_argument("--files", nargs="+", type=int)
    add.set_defaults(func=addwins)

    # modify existing record of wins
    modify = action.add_parser("modify", aliases=["mod", "m"])
    modify.add_argument("firstname", type=str)
    modify.add_argument("lastname", type=str)
    modify.add_argument("--have", default=True, action=argparse.BooleanOptionalAction)
    modify.add_argument("--rating", type=int)
    modify.add_argument("--soc")
    modify.add_argument("--size", type=float)
    modify.add_argument("--files", nargs="+", type=int)
    modify.add_argument("--ln")
    modify.add_argument("--fn")
    modify.set_defaults(func=modifywins)

    # delete existing entries
    delete = action.add_parser("delete", aliases=["d"])
    delete.add_argument("firstname", type=str)
    delete.add_argument("lastname", type=str)
    delete.set_defaults(func=deletewins)

    args = parser.parse_args()
    # valid command, read in json
    with open("winlog.json", "r+") as wl:
        data = json.loads(wl.read())
        args.func(args, data, wl)


if __name__ == "__main__":
    main()
