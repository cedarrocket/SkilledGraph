import os


def average(values):
    return sum(values) / len(values)


def run_job(user_command):
    return os.system(user_command)
