import os
import queue
import time
import traceback
from datetime import datetime
from threading import Thread

import requests
import unidecode
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.openapi.models import Response

solr_host = os.getenv("SOLR_HOST", "host.docker.internal")
conf_path = os.getenv("CONF_PATH", "/mycore_config/conf/")
synonyms_path = os.getenv("SYNONYMS_PATH", "/mycore_config/conf/synonyms.txt")
synonym_lines_len = 0#why am i even tracking this TODO just use len on synonyms by line
loaded = False

run_interval = .5 #seconds
update_queue = queue.Queue()
synonyms_by_line = {}
lines_by_synonyms = {}

app = FastAPI(docs_url="/")

@app.post("/update")
async def add_synonym_to_queue(word_list:list):
    try:
        unnaccented_words = [unidecode.unidecode(word) for word in word_list]
        update_queue.put(unnaccented_words)
        return Response(status_code=201)
    except:
        return []

def consume_queue(update_queue):
    while True:
        try:
            if not update_queue.empty():
                process_synonyms(update_queue.get())
        except:
            print(datetime.now().isoformat() + " " + traceback.format_exc())
        time.sleep(run_interval)

def process_synonyms(synonym_list):
    global synonym_lines_len

    #base case no synonyms
    if synonym_lines_len == 0:
        synonyms_by_line[0] = synonym_list
        for synonym in synonym_list:
            lines_by_synonyms[synonym] = 0
        synonym_lines_len = 1
        
    else:
        #check if there is a match on any synonym and append it
        appendded = False
        for synonym in synonym_list:
            if synonym in lines_by_synonyms:
                idx = lines_by_synonyms[synonym]
                synonyms_by_line[idx] = list(dict.fromkeys(synonyms_by_line[idx] + synonym_list))
                for synonym in synonym_list:
                    if synonym not in lines_by_synonyms:
                        lines_by_synonyms[synonym] = idx
                appendded = True
                break
        
        #if its a new one then ...
        if not appendded:
            synonym_lines_len = synonym_lines_len + 1
            synonyms_by_line[synonym_lines_len] = list(dict.fromkeys(synonym_list))
            for synonym in synonym_list:
                if synonym not in lines_by_synonyms:
                    lines_by_synonyms[synonym] = synonym_lines_len
            pass

    dump_synonyms()

    #update solr
    requests.get(f"http://{solr_host}:8983/solr/admin/cores?action=RELOAD&core=mycore")

    pass

def load_synonyms():
    with open(synonyms_path) as f:
        lines = f.read().splitlines()
        global synonym_lines_len
        synonym_lines_len = len(lines)
        for idx, line in enumerate(lines):
            words = line.split(',')
            for word in words:
                lines_by_synonyms[word] = idx

                if idx not in synonyms_by_line:
                    synonyms_by_line[idx] = []
                synonyms_by_line[idx].append(word)
    

def dump_synonyms():

    #wipe existing temp
    if os.path.exists(conf_path+"synonyms2.txt"):
        os.remove("synonyms2.txt")

    textfile = open(conf_path+"synonyms2.txt", "w")
    for idx in synonyms_by_line:
        line = ','.join(synonyms_by_line[idx]) + '\n'
        textfile.write(line)
    textfile.close()


    #replace old synonyms with new synonyms making an atomic change
    os.replace(conf_path+'synonyms2.txt', synonyms_path)

load_synonyms()

t1 = Thread(target = consume_queue, args=(update_queue,))
t1.setDaemon(True)
t1.start()


if __name__=="__main__":
    update_queue.put(["beneficiario","destinatario","ganador","receptor","titular","ganador","medallista"])
    uvicorn.run("main:app",host='localhost', port=8092, reload=True, debug=True)
