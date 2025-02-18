import os
import hashlib
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from db import *  # Make sure the 'db' module is available
from notify import apobj
import uvicorn  # Import uvicorn

FILES_DIRECTORY = os.getenv("FILES_DIRECTORY", "./monito")

app = FastAPI()
templates = Jinja2Templates(directory="templates")
def calculate_hash(file_path):
    with open(file_path, "rb") as file:
        sha256_hash = hashlib.sha256()
        while chunk := file.read(8192):
            sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

def on_modified(event):
    if event.is_directory:
        return

    apobj.notify(
    body=f"👀 Name: {event.src_path}\n#️⃣ Hash: {calculate_hash(event.src_path)}\n⏰ Date: {str(datetime.now())}",
    title='⚠️ == File Modified == ⚠️'
    )

    path = event.src_path
    filename = os.path.basename(path)
    hash_value = calculate_hash(path)
    file_info = get_file(filename, path)
    if not file_info:
        insert_file(filename, path, hash_value)
    try:
        if file_info.hash != hash_value:
            update_file(filename, path, hash_value)
    except:
        pass

def first_run():
    for root, dirs, files in os.walk(FILES_DIRECTORY):
        for file in files:
            path = os.path.join(root, file)
            hash_value = calculate_hash(path)
            file_info = get_file(file, path)
            if not file_info:
                insert_file(file, path, hash_value)
            if file_info.hash != hash_value:
                update_file(file, path, hash_value)

@app.get("/")
def json_data():
    files = get_files()
    files_final = []
    for i in files:
        files_final.append({"filename": i.filename, 
                            "path": i.path, 
                            "hash": i.hash, 
                            "old_hash": i.old_hash,
                            "last_modified": i.last_modified})
    return {"files": files_final}

@app.get("/board")
def dashboard(request: Request):
    files = get_files()
    files_final = []
    for i in files:
        files_final.append({"filename": i.filename, 
                            "path": i.path, 
                            "hash": i.hash, 
                            "old_hash": i.old_hash,
                            "last_modified": i.last_modified})
    return templates.TemplateResponse("dashboard.html", {"request": request, "files_data": files_final})


@app.get("/files/{filename:path}")
def read_file(filename: str):
    secure_filename = werkzeug.utils.secure_filename(filename)
    print(secure_filename)
    path = os.path.join(FILES_DIRECTORY, secure_filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found.")
    hash_value = calculate_hash(path)
    file_info = get_file(secure_filename, path)
    if not file_info:
        insert_file(secure_filename, path, hash_value)

    if file_info.hash != hash_value:
        update_file(secure_filename, path, hash_value)
        return {"status": "File Modified", "filename": secure_filename, "path": path, "hash": hash_value, "old_hash": file_info[4], "last_modified": file_info[5]}

    return {"status": "OK.","filename": secure_filename, "path": path, "hash": hash_value, "old_hash": file_info.old_hash, "last_modified": file_info.last_modified}

@app.get("/files")
def read_files():
    files = get_files()
    files_final = []
    for i in files:
        files_final.append({"filename": i.filename, 
                            "path": i.path, 
                            "hash": i.hash, 
                            "old_hash": i.old_hash,
                            "last_modified": i.last_modified})
    return {"files": files_final}


if __name__ == "__main__":
    create_table()
    observer = Observer()
    event_handler = FileSystemEventHandler()  # Use the correct class name
    event_handler.on_modified = on_modified
    observer.schedule(event_handler, path=FILES_DIRECTORY, recursive=True)
    observer.start()

    # Run the FastAPI app using Uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




