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

You need [Git](https://git-scm.com/), [Docker Desktop](https://www.docker.com/products/docker-desktop/), the [MongoDB Shell](https://www.mongodb.com/try/download/shell) (`mongosh`) and [Python 3](https://www.python.org/downloads/).

### 1. Get the code

```bash
git clone https://github.com/leonart92/No_SQL_project.git
cd No_SQL_project
```

### 2. Start MongoDB

Open Docker Desktop, then create the container. It listens on port 27018.

```bash
docker run -d --name mongo-local -p 27018:27017 mongo:7
```

### 3. Create and fill the database

```bash
mongosh "mongodb://localhost:27018" --file DBScript.txt
```

### 4. Install the Python dependency

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows, use `.venv\Scripts\pip` and `.venv\Scripts\python` instead.

### 5. Run the application

```bash
.venv/bin/python MongoDB.py
```

## Starting again later

The container keeps its data. Next time, only two commands are needed:

```bash
docker start mongo-local
.venv/bin/python MongoDB.py
```

To go back to the original 20 documents, remove the container and repeat steps 2 and 3:

```bash
docker rm -f mongo-local
```

## Running the queries

The 15 queries are at the end of `DBScript.txt`. Running the file with `--file` executes them without printing their results, so to see the results open a shell and paste them one at a time:

```bash
mongosh "mongodb://localhost:27018/cleanupDB"
```

## Connection settings

The application connects to `mongodb://localhost:27018` by default. Set `MONGO_URI` to use another server, or to connect as the `Admin` user created by the script:

```bash
MONGO_URI="mongodb://Admin:pa33word@localhost:27018/?authSource=cleanupDB" .venv/bin/python MongoDB.py
```
