# Fixture file for minisast — every pattern below is intentionally flawed
# so the scanner has something to find. Nothing here is a real credential
# and none of these code paths are ever executed.
import hashlib
import subprocess

api_key = "sk-fake-1234567890abcdef"  # hardcoded-secret
db_password = "hunter2"               # hardcoded-secret


def run_user_command(user_input):
    subprocess.call(user_input, shell=True)  # shell-injection


def evaluate(expr):
    return eval(expr)  # eval-exec


def weak_digest(data):
    return hashlib.md5(data).hexdigest()  # weak-hash


def weak_digest_for_cache_key(data):
    # non-security use, reviewed and accepted
    return hashlib.md5(data).hexdigest()  # minisast: ignore[weak-hash]


def lookup_user(cursor, username):
    cursor.execute(f"SELECT * FROM users WHERE name = '{username}'")  # sql-injection
