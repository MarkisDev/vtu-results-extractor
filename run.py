from enums import ExtractorEnums as Const
from extractor import Extractor
from file import File
import os
from db import Database
import re
import eel
import time

eel.init('ui')
db = Database(os.getcwd())


@eel.expose
def extract(usns, link, reval):
    try:
        count = 0
        skipped = []
        link = link.replace('https://', '').replace('http://', '')
        resultCode = link.split('/')[1]
        indexUrl = "/".join([Const.BASE_DOMAIN.value,
                            resultCode, Const.INDEX_FILE.value])
        resultUrl = "/".join([Const.BASE_DOMAIN.value,
                             resultCode, Const.RESULT_FILE.value])
        usnList = [usn.lower() for usn in usns.split(",")]
        extractorObj = Extractor(Const.BASE_DOMAIN.value,
                                 indexUrl, resultUrl)
        for usn in usnList:
            # Checking if USN is valid
            if re.match(r'\d[a-zA-z]{2}\d{2}[a-zA-z]{2}\d{3,}', usn):
                # Checking is USN is not in db
                if not db.doesUsnExist(usn, reval):
                    res = extractorObj.extract(usn.lower(), reval)
                    eel.queue(usn)
                    if res == False:
                        skipped.append(usn)
                    else:
                        time.sleep(10)
                        count+=1
                        if count == 30:
                            time.sleep(330)
                            count = 0
            else:
                skipped.append(usn)
        return {"status": True, "len": len(usnList)-len(skipped), "skipped": skipped}
    except Exception as e:
        print("Error occured while running script for extraction!", e)
        return {"status": False}


@eel.expose
def generate():
    try:
        skipped = []
        reg, rev = db.getAllUsn()
        # Generating for reg files
        for usn in reg:
            reval = False
            maxSem = db.findMaxSem(usn.lower(), reval)[0][0]
            # Can be none if USN doesn't exist
            if maxSem:
                for i in range(1, int(maxSem)+1):
                    fileObj = File(
                        i, reval, Const.OUTPUT_FOLDER_NAME.value)
                    fileObj.addData(db.getData(
                        usn.lower(), reval, i))
            else:
                skipped.append(usn)
        # Generating for reval files
        for usn in rev:
            reval = True
            maxSem = db.findMaxSem(usn.lower(), reval)[0][0]
            # Can be none if USN doesn't exist
            if maxSem:
                for i in range(1, int(maxSem)+1):
                    fileObj = File(
                        i, reval, Const.OUTPUT_FOLDER_NAME.value)
                    fileObj.addData(db.getData(
                        usn.lower(), reval, i))
            else:
                skipped.append(usn)
        return {"status": True, "len": (len(reg)+len(rev))-len(skipped), "skipped": skipped}

    except:
        print("Error occured while generating!")
        return {"status": False}


@eel.expose
def truncate():
    try:
        if db.truncate():
            return {"status": True}
        else:
            return {"status": False}
    except Exception as e:
        print("Error occured while truncating!", e)
        return {"status": False}


eel.start('index.html')
