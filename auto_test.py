#!/usr/bin/env python
import os, sys, optparse, logging, glob, stat, json
logger = logging.getLogger(__name__)

#set up lists to be looped through later
global dirs, nodes, ranks_per_node
dirs = ["in_container/", "out_container/", "same_nodes/", "different_nodes/"]
nodes = ["1", "2", "4", "8"]
ranks_per_node = ["8", "16", "32", "64", "128"]


def main():
    #create a base directory
    os.mkdir("benchmarking_directory/")
    os.chdir("benchmarking_directory/")
    #make directories for in and out of the container
    os.mkdir(dirs[0])
    os.mkdir(dirs[1])
    i = 0
    while(i < 2):
        #1st time through, this makes the directories for inside a container and makes the settings.txt and submit.sh files
        #second time through it does the same but for outside the container
        os.chdir(dirs[i])
        os.mkdir(dirs[2])
        os.chdir(dirs[2])
        if(dirs[i] == dirs[1]):
            for d in range(len(ranks_per_node)):
                #creating files and directories for each different mpi rank per node to be tested
                create_submit(False, True, ranks_per_node[d])
        else:
            for d in range(len(ranks_per_node)):
                create_submit(True, True, ranks_per_node[d])
        os.chdir("..")
        os.mkdir(dirs[3])
        os.chdir(dirs[3])
        if (dirs[i] == dirs[1]):
            for d in range(len(ranks_per_node)):
                create_submit(False, False, ranks_per_node[d])
        else:
            for d in range(len(ranks_per_node)):
                create_submit(True, False, ranks_per_node[d])
        os.chdir("..")
        os.chdir("..")
        i += 1

def create_submit(use_container, same_nodes, num_ranks):
    job_num = 'numranks' + str(num_ranks)

    job_dir = os.getcwd() + '/' + job_num

    logger.info('building job directory: %s', job_dir)
    logger.info('    num_ranks: %5d   use_container: %6s  same_nodes: %6s', int(num_ranks), use_container, same_nodes)

    if os.path.exists(job_dir):
        raise Exception('job directory already exists: %s' % job_dir)
    os.mkdir(job_dir)

    # dump settings to text file for record keeping
    settings = {'num_ranks': int(num_ranks),
                'use_container': use_container,
                'same_nodes' : same_nodes
                }
    json.dump(settings, open(job_dir + '/settings.txt', 'w'))

    # copy EVNT and json files  from base job to new job dir
    copy_base_dir(job_dir)

    # create submit file
    queue = 'default'
    if int(num_ranks) <= 8:
        queue = 'debug-flat-quad'
    submit = submit_template.format(num_ranks=num_ranks,
                                    queue=queue,
                                    job_dir=job_dir,
                                    job_num=job_num,
                                    same_nodes=same_nodes,
                                    use_container=use_container)
    open(job_dir + '/submit.sh', 'w').write(submit)
    os.chmod(job_dir + '/submit.sh', stat.S_IRWXU | stat.S_IRWXG | stat.S_IXOTH | stat.S_IROTH)
    os.chdir(job_dir)
    os.system('qsub submit.sh')
    os.chdir("..")

def copy_base_dir(job_dir,base_dir='basejob'):

   # copy EVNT files
   os.system('cp -d ' + base_dir + '/EVNT* ' + job_dir)

   # copy json files
   os.system('cp ' + base_dir + '/*json* ' + job_dir)


submit_template = '''#!/bin/bash
#COBALT -n 128
#COBALT -t 120
#COBALT -q {queue}
#COBALT -A datascience
#COBALT --jobname {job_num}
#COBALT --cwd {job_dir}

SAME_NODES={same_nodes}
if [ "$SAME_NODES" = "TRUE" ] || [ "$SAME_NODES" = "true" ] || [ "$SAME_NODES" = "True" ]; then
   #COBALT --attrs location=0,1,2,3,4,5,6,7
   echo SAME NODES TRUE
fi

RANKS_PER_NODE={num_ranks}
NUM_NODES=$COBALT_JOBSIZE
TOTAL_RANKS=$(( $COBALT_JOBSIZE * $RANKS_PER_NODE ))


# app build with GNU not Intel
module swap PrgEnv-intel PrgEnv-gnu

if [ "$USE_CONTAINER" = "TRUE" ] || [ "$USE_CONTAINER" = "true" ] || [ "$USE_CONTAINER" = "True" ]; then
   #run benchmark without singularity
   echo RUNNING OUTSIDE OF CONTAINER
   echo ONE NODE
   aprun -n $RANKS_PER_NODE -N $RANKS_PER_NODE /home/sgww/osu_bench/mpi/collective/osu_bcast
   echo TWO NODES
   aprun -n $(($RANKS_PER_NODE*2)) -N $RANKS_PER_NODE /home/sgww/osu_bench/mpi/collective/osu_bcast
   echo FOUR NODES
   aprun -n $(($RANKS_PER_NODE*4)) -N $RANKS_PER_NODE /home/sgww/osu_bench/mpi/collective/osu_bcast
   echo EIGHT NODES
   aprun -n $(($RANKS_PER_NODE*8)) -N $RANKS_PER_NODE /home/sgww/osu_bench/mpi/collective/osu_bcast
   wait
fi

# Use Cray's Application Binary Independent MPI build
module swap cray-mpich cray-mpich-abi


# include CRAY_LD_LIBRARY_PATH in to the system library path
export LD_LIBRARY_PATH=$CRAY_LD_LIBRARY_PATH:$LD_LIBRARY_PATH
# also need this additional library
export LD_LIBRARY_PATH=/opt/cray/wlm_detect/1.3.2-6.0.6.0_3.8__g388ccd5.ari/lib64/:$LD_LIBRARY_PATH
# in order to pass environment variables to a Singularity container create the variable
# with the SINGULARITYENV_ prefix
export SINGULARITYENV_LD_LIBRARY_PATH=$LD_LIBRARY_PATH
# print to log file for debug
echo $SINGULARITYENV_LD_LIBRARY_PATH


# -n <total MPI ranks>
# -N <MPI ranks per node>
export SINGULARITYENV_LD_LIBRARY_PATH=/lib64:/lib:/usr/lib64:/usr/lib:$SINGULARITYENV_LD_LIBRARY_PATH
# aprun -n 1 -N 1 singularity exec testbuild2.simg /bin/bash -c "echo \$LD_LIBRARY_PATH"

USE_CONTAINER={use_container}
if [ "$USE_CONTAINER" = "TRUE" ] || [ "$USE_CONTAINER" = "true" ] || [ "$USE_CONTAINER" = "True" ]; then
   echo RUNNING INSIDE CONTAINER
   echo ONE NODE
   aprun -n $RANKS_PER_NODE -N $RANKS_PER_NODE singularity run -B /opt:/opt:ro -B /var/opt:/var/opt:ro --app mbw_mr /home/sgww/updatedbenchcontainer
   echo TWO NODES
   aprun -n $(($RANKS_PER_NODE*2)) -N $RANKS_PER_NODE singularity run -B /opt:/opt:ro -B /var/opt:/var/opt:ro --app mbw_mr /home/sgww/updatedbenchcontainer
   echo FOUR NODES
   aprun -n $(($RANKS_PER_NODE*4)) -N $RANKS_PER_NODE singularity run -B /opt:/opt:ro -B /var/opt:/var/opt:ro --app mbw_mr /home/sgww/updatedbenchcontainer
   echo EIGHT NODES
   aprun -n $(($RANKS_PER_NODE*8)) -N $RANKS_PER_NODE singularity run -B /opt:/opt:ro -B /var/opt:/var/opt:ro --app mbw_mr /home/sgww/updatedbenchcontainer
   wait
fi
'''

if __name__ == "__main__":
    main()