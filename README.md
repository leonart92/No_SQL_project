# Community Cleanup Tracker

MongoDB group assignment (CA2) by Group 5: Edouard Dupuch, Leonart Heurteux, Brice Laurent and Mael Mangata.

Dublin City Council wants to organise community cleanups. This project stores the cleanup events and the volunteers in MongoDB, answers reporting questions with queries, and gives council staff a small console application to manage the data.

## What is in the repository

| File | Purpose |
|---|---|
| `DBSchema.doc` | Schema design: fields, data types and the reasons behind the design |
| `DBScript.txt` | MongoDB script: collections, validation rules, indexes, sample data, admin role and user, and the 15 queries |
| `MongoDB.py` | Python console application built with PyMongo |
| `requirements.txt` | Python dependency (`pymongo`) |
| `tests/` | Shell scripts the team used to test the database locally |

## How the project is built

The database is called `cleanupDB` and has two collections.

- `cleanupEvents`: one document per cleanup, with its date, zone, GPS location, organiser, the waste collected per type, its duration and its status.
- `volunteers`: one document per volunteer, with contact details, address, skills, hours logged and badges.

Small data that belongs to a single document is embedded: the organiser, the waste entries and the address. Events and volunteers have a many-to-many relationship, so they reference each other by `_id` instead: an event lists its volunteers and a volunteer lists the events attended.

`DBScript.txt` creates both collections with a `$jsonSchema` validator, so MongoDB refuses any document that does not follow the schema. It also creates a `2dsphere` index for location searches and a unique index on the volunteer email, then inserts 10 documents in each collection.

`MongoDB.py` connects to that database and loops over a menu: pick a collection, then pick an action.

1. Display all documents
2. Add a new document
3. Update a document
4. Delete a document
5. Search documents by keyword
6. Exit system

## Getting started from scratch

You need three things: a MongoDB server, the MongoDB Shell (`mongosh`) and Python 3. Docker is not needed. Every command below is run from the project folder, the one that contains `DBScript.txt` and `MongoDB.py`.

### 1. Install MongoDB and mongosh

**Windows**

1. Download and run the MongoDB Community Server installer (`.msi`) from https://www.mongodb.com/try/download/community. Choose the Complete setup and keep the option "Install MongoD as a Service" ticked, so MongoDB starts by itself.
2. Download and run the MongoDB Shell installer (`.msi`) from https://www.mongodb.com/try/download/shell.
3. Close and reopen your terminal so that the `mongosh` command is found.

**macOS** (with [Homebrew](https://brew.sh/))

```bash
brew tap mongodb/brew
```

```bash
brew install mongodb-community
```

```bash
brew services start mongodb-community
```

This installs `mongosh` as well. On both systems MongoDB now listens on `localhost:27017`, which is where the application looks by default.

### 2. Install Python

Install Python 3 from https://www.python.org/downloads/. On Windows, tick "Add python.exe to PATH" in the installer.

### 3. Create and fill the database

The same command works on Windows and macOS:

```bash
mongosh --file DBScript.txt
```

### 4. Install the Python dependency

**Windows** (PowerShell or Command Prompt)

```bash
py -m venv .venv
```

```bash
.venv\Scripts\pip install pymongo
```

**macOS**

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install pymongo
```

### 5. Run the application

**Windows**

```bash
.venv\Scripts\python MongoDB.py
```

**macOS**

```bash
.venv/bin/python MongoDB.py
```

## Starting again later

MongoDB keeps running in the background and keeps its data, so only step 5 is needed.

To go back to the original 20 documents, remove the admin user and role, then run the script again:

```bash
mongosh cleanupDB --eval "db.dropAllUsers(); db.dropAllRoles()"
```

```bash
mongosh --file DBScript.txt
```

## Running the queries

The 15 queries are at the end of `DBScript.txt`. Running the file with `--file` executes them without printing their results, so to see the results open a shell and paste them one at a time:

```bash
mongosh cleanupDB
```

## Using Docker instead

If Docker is installed, it can replace step 1. Start a MongoDB container, then follow steps 2 to 5 as written:

```bash
docker run -d --name mongo-local -p 27017:27017 mongo:7
```

Next time, start it again with `docker start mongo-local`.

## Connection settings

The application connects to `mongodb://localhost:27017` by default. Set the `MONGO_URI` variable to use another server, for example to connect as the `Admin` user created by the script.

**Windows** (PowerShell)

```bash
$env:MONGO_URI="mongodb://Admin:pa33word@localhost:27017/?authSource=cleanupDB"
```

```bash
.venv\Scripts\python MongoDB.py
```

**macOS**

```bash
MONGO_URI="mongodb://Admin:pa33word@localhost:27017/?authSource=cleanupDB" .venv/bin/python MongoDB.py
```
