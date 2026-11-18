import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from bson import json_util
from pymongo import MongoClient
from pymongo.errors import PyMongoError

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "DBScript.txt"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27018")
DB_NAME = "cleanupDB"


def run_mongosh(*args):
    return subprocess.run(
        ["mongosh", MONGO_URI, "--quiet", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )


def run_script():
    return run_mongosh("--file", str(SCRIPT))


def load_queries():
    """Read the queries from DBScript.txt, so the tests run the exact code of the script."""
    text = SCRIPT.read_text(encoding="utf-8")
    pattern = re.compile(r"^// Query (\d+):[^\n]*\n(.*?)(?=^// Query \d+:|\Z)", re.S | re.M)
    return {int(number): code.strip().rstrip(";").strip() for number, code in pattern.findall(text)}


QUERIES = load_queries()


def run_query(number):
    code = f"""
db = db.getSiblingDB("{DB_NAME}");
const result = (
{QUERIES[number]}
);
const value = result && typeof result.toArray === "function" ? result.toArray() : result;
print(EJSON.stringify(value, {{ relaxed: false }}));
"""
    process = run_mongosh("--eval", code)
    assert process.returncode == 0, process.stderr
    return json_util.loads(process.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="session")
def client():
    if shutil.which("mongosh") is None:
        pytest.skip("mongosh is not installed")
    mongo = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    try:
        mongo.admin.command("ping")
    except PyMongoError:
        pytest.skip(f"no MongoDB server at {MONGO_URI}")
    yield mongo
    mongo.close()


@pytest.fixture
def db(client):
    process = run_script()
    assert process.returncode == 0, process.stderr
    return client[DB_NAME]
