import os, json, shutil, argparse

parser = argparse.ArgumentParser(description='Pass uncategorized and categorized directory paths')
parser.add_argument('src', type=str, help='path to the src dir')
parser.add_argument('dst', type=str, help='path to the dst dir')
args = parser.parse_args()

print('First file path:', args.src)
print('Second file path:', args.dst)

rating_folders = ['3','4','5','failed']
for rating_folder in rating_folders:
    if not os.path.exists(os.path.join(args.dst, rating_folder)):
        os.makedirs(os.path.join(args.dst, rating_folder))

with open('/Users/dan/Desktop/projects/megalinks/winlog.json') as jf:
    jdata = json.loads(jf.read())
    # folders = [f for f in os.listdir(args.src) if not f.startswith('.')]
    folders = [f for f in  next(os.walk(args.src))[1] if not f.startswith('.')]
    for folder in folders:
        newname = folder
        rating_group = 'failed'

        splitname = folder.split()
        fn, ln = splitname[0].lower(), splitname[1].lower()
        if fn in jdata:
            lnrecords = jdata[fn]
            for lnrecord in lnrecords:
                if ln in lnrecord['lastname']:
                    # found
                    rating_group = lnrecord['rating']
                    if len(splitname) > 2:
                        # rename
                        newname = f"{fn.capitalize()} {ln.capitalize()} {' '.join(w for w in splitname[2:])}"
                    break
        shutil.move(os.path.join(args.src, folder), os.path.join(args.dst, str(rating_group), newname))