#!/usr/bin/env python
import os, sys, optparse, logging, glob, stat, json

global dirs, nodes, ranks_per_node
dirs = ["in_container/", "out_container/", "same_nodes/", "different_nodes/"]
nodes = ["1", "2", "4", "8"]
ranks_per_node = ["8", "16", "32", "64", "128"]


def main():
    os.mkdir("benchmarking_directory/")
    os.chdir("benchmarking_directory/")
    os.mkdir(dirs[0])
    os.mkdir(dirs[1])
    for i in dirs:
        os.chdir(dirs[i])
        os.mkdir(dirs[2])
        os.mkdir(dirs[3])
        os.chdir("..")
        i += 1


if __name__ == "__main__":
    main()