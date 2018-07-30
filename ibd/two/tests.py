from one import *

import test_data

version_streams = test_data.make_version_streams()

def test_read_version_0():
    n = read_version(version_streams[0])
    assert n == 70015

def test_read_version_1():
    n = read_version(version_streams[1])
    assert n == 60001

def test_read_version_2():
    n = read_version(version_streams[2])
    assert n == 106
