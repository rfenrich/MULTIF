#!/usr/bin/env python

## \file interface.py
#  \brief python package interfacing with the SU2 suite
#  \author T. Lukaczyk, F. Palacios
#  \version 4.1.2 "Cardinal"
#
# SU2 Lead Developers: Dr. Francisco Palacios (Francisco.D.Palacios@boeing.com).
#                      Dr. Thomas D. Economon (economon@stanford.edu).
#
# SU2 Developers: Prof. Juan J. Alonso's group at Stanford University.
#                 Prof. Piero Colonna's group at Delft University of Technology.
#                 Prof. Nicolas R. Gauger's group at Kaiserslautern University of Technology.
#                 Prof. Alberto Guardone's group at Polytechnic University of Milan.
#                 Prof. Rafael Palacios' group at Imperial College London.
#
# Copyright (C) 2012-2016 SU2, the open-source CFD code.
#
# SU2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# SU2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with SU2. If not, see <http://www.gnu.org/licenses/>.

# ----------------------------------------------------------------------
#  Imports
# ----------------------------------------------------------------------

import os, sys, shutil, copy
import subprocess
from ..io import Config
from ..util import which

# ------------------------------------------------------------
#  Setup
# ------------------------------------------------------------


#print "os.environ['SU2_RUN']  = %s\n" % os.environ['SU2_RUN'] ;
#SU2_RUN = os.environ['SU2_RUN'] 
#sys.path.append( SU2_RUN )
#sys.path.append('/usr/local/bin/SU2_2/');

SU2_RUN="";

# SU2 suite run command template
base_Command = os.path.join(SU2_RUN,'%s')

# check for slurm
slurm_job = os.environ.has_key('SLURM_JOBID')

#check for tacc
tacc_job = os.environ.has_key('TACC_PUBLIC_MACHINE')

# set mpi command
if slurm_job:
    # SU2_CFD 5000 iters on 32 cores ~ 45 minutes 
    mpi_Command = 'salloc --ntasks=%i --time=%s mpirun --mca mpi_cuda_support 0 --max-restarts 2 --enable-recovery --display-map --display-allocation --report-bindings %s'
#    mpi_Command = 'salloc --ntasks=%i --time=0-01:00 mpirun --mca mpi_cuda_support 0 --max-restarts 2 --enable-recovery --display-map --display-allocation --report-bindings %s'
#    mpi_Command = 'srun -mpi openmpi --verbose --verbose -n %i %s'
    #mpi_Command = 'mpirun --mca mpi_cuda_support 0 --map-by core:SPAN --display-map --display-allocation --report-bindings -n %i %s'
    # RUNS IN NEW ALLOCATION mpi_Command = 'salloc -n 4 mpirun --mca mpi_cuda_support 0 --map-by core:SPAN --display-map --display-allocation --report-bindings -n %i %s'
    #mpi_Command = 'mpirun --mca mpi_cuda_support 0 --bind-to none --display-map --display-allocation --report-bindings -n %i %s'
    if tacc_job:
        mpi_Command = 'ibrun -o 0 -n %i %s'
elif not which('mpirun') is None:
    mpi_Command = 'mpirun -n %i %s'
elif not which('mpiexec') is None:
    mpi_Command = 'mpiexec -n %i %s'
else:
    mpi_Command = ''
    
from .. import EvaluationFailure, DivergenceFailure
return_code_map = {
    1 : EvaluationFailure ,
    2 : DivergenceFailure ,
}

# -----------------------------------------------------------
# Helper functions
# ----------------------------------------------------------

def getAndWriteSlurmVariables(label):
    """
    Get and write Slurm environment variables to a file so we can see what is
    going on with Slurm.
    """

    envVars = os.environ
    with open('%s_slurm_vars.txt'%label,'w') as f:
        for v in envVars:
            if 'SLURM' in v:
                f.write('%s: %s\n' % (v, os.getenv(v)))
    # Write PATH and LD_LIBRARY_PATH varibles as well
    with open('%s_path.txt'%label,'w') as f:
        f.write('PATH: %s\n' % os.getenv('PATH'))
        f.write('LD_LIBRARY_PATH: %s\n' % os.getenv('LD_LIBRARY_PATH'))
    # Write OpenMPI environment variables as well
    with open('%s_ompi_vars.txt'%label,'w') as f:
        for v in envVars:
            if 'OMPI' in v:
                f.write('%s: %s\n' % (v, os.getenv(v)))
  
    return

 
# ------------------------------------------------------------
#  SU2 Suite Interface Functions
# ------------------------------------------------------------

def CFD(config):
    """ run SU2_CFD
        partitions set by config.NUMBER_PART
    """
		
    base='';

    if 'SU2_RUN' in config:
        print "SU2_RUN IN DICT";
        base = "{0}".format(config['SU2_RUN']);
		
    config.pop("SU2_RUN", None);
		
    konfig = copy.deepcopy(config)
    
    direct_diff = not konfig.get('DIRECT_DIFF',"") in ["NONE", ""]
		
    auto_diff = konfig.MATH_PROBLEM == 'DISCRETE_ADJOINT'

    if direct_diff:
        tempname = 'config_CFD_DIRECTDIFF.cfg'

        konfig.dump(tempname)

        processes = konfig['NUMBER_PART']

        the_Command = 'SU2_CFD_DIRECTDIFF ' + tempname

    elif auto_diff:
        tempname = 'config_CFD_AD.cfg'
        konfig.dump(tempname)

        processes = konfig['NUMBER_PART']

        the_Command = 'SU2_CFD_AD ' + tempname

    else:
        tempname = 'config_CFD.cfg'
        konfig.dump(tempname)
    
        processes = konfig['NUMBER_PART']
    
        the_Command = 'SU2_CFD ' + tempname

		
    the_Command = os.path.join(base,the_Command);
			
    the_Command = build_command( the_Command , processes )
		
	
    return_code = run_command( the_Command )
    
    return return_code

def MSH(config):
    """ run SU2_MSH
        partitions set by config.NUMBER_PART
        currently forced to run serially
    """    
    konfig = copy.deepcopy(config)
    
    tempname = 'config_MSH.cfg'
    konfig.dump(tempname)
    
    # must run with rank 1
    processes = konfig['NUMBER_PART']
    processes = min([1,processes])    
    
    the_Command = 'SU2_MSH ' + tempname
    the_Command = build_command( the_Command , processes )
    run_command( the_Command )
    
    #os.remove(tempname)
    
    return

def DEF(config):
    """ run SU2_DEF
        partitions set by config.NUMBER_PART
        forced to run in serial, expects merged mesh input
    """

    base='';
    if 'SU2_RUN' in config:
    	print "SU2_RUN IN DICT";
    	base = "{0}/".format(config['SU2_RUN']);
    	del config['SU2_RUN'];


    konfig = copy.deepcopy(config)
    
    tempname = 'config_DEF.cfg'
    konfig.dump(tempname) 
    
    # must run with rank 1
    processes = konfig['NUMBER_PART']
    
    the_Command = 'SU2_DEF ' + tempname
	
    the_Command = os.path.join(base,the_Command);
	
    the_Command = build_command( the_Command , processes )

    run_command( the_Command )
    
    #os.remove(tempname)
    
    return

def DOT(config):
	""" run SU2_DOT
	    partitions set by config.NUMBER_PART
	"""  
	
	base='';
	
	if 'SU2_RUN' in config:
		print "SU2_RUN IN DICT";
		base = "{0}".format(config['SU2_RUN']);
		del config['SU2_RUN'];
	  
	
	
	konfig = copy.deepcopy(config)
	
	
	auto_diff = konfig.MATH_PROBLEM == 'DISCRETE_ADJOINT' or konfig.get('AUTO_DIFF','NO') == 'YES'
	
	if auto_diff:
	
	    tempname = 'config_DOT_AD.cfg'
	    konfig.dump(tempname)
	
	    processes = konfig['NUMBER_PART']
	
	    the_Command = 'SU2_DOT_AD ' + tempname
	else:
		
		tempname = 'config_DOT.cfg'
		konfig.dump(tempname)
		
		processes = konfig['NUMBER_PART']
		
		the_Command = 'SU2_DOT ' + tempname
		
		
	the_Command = os.path.join(base,the_Command);
	
	#print " -- Running SU2_DOT. Command = %s\n" % the_Command;
	
	
	the_Command = build_command( the_Command , processes )
	run_command( the_Command )
	
	#os.remove(tempname)
	
	return

def GEO(config):
    """ run SU2_GEO
        partitions set by config.NUMBER_PART
        forced to run in serial
    """    
    konfig = copy.deepcopy(config)
    
    tempname = 'config_GEO.cfg'
    konfig.dump(tempname)   
    
    # must run with rank 1
    processes = konfig['NUMBER_PART']
        
    the_Command = 'SU2_GEO ' + tempname
    the_Command = build_command( the_Command , processes )
    run_command( the_Command )
    
    #os.remove(tempname)
    
    return
        
def SOL(config):
    """ run SU2_SOL
      partitions set by config.NUMBER_PART
    """
  
    konfig = copy.deepcopy(config)
    
    tempname = 'config_SOL.cfg'
    konfig.dump(tempname)
  
    # must run with rank 1
    processes = konfig['NUMBER_PART']
    
    the_Command = 'SU2_SOL ' + tempname
    the_Command = build_command( the_Command , processes )
    run_command( the_Command )
    
    #os.remove(tempname)
    
    return

def SOL_FSI(config):
    """ run SU2_SOL for FSI problems
      partitions set by config.NUMBER_PART
    """
  
    konfig = copy.deepcopy(config)
    
    tempname = 'config_SOL.cfg'
    konfig.dump(tempname)
  
    # must run with rank 1
    processes = konfig['NUMBER_PART']
    
    the_Command = 'SU2_SOL ' + tempname + ' 2'
    the_Command = build_command( the_Command , processes )
    run_command( the_Command )
    
    #os.remove(tempname)
    
    return


# ------------------------------------------------------------
#  Helper functions
# ------------------------------------------------------------

def build_command( the_Command , processes=0, base='' ):
    """ builds an mpi command for given number of processes """

    if base == '':
        the_Command = base_Command % the_Command;
    else:
        the_Command = base % the_Command;
    
    if processes > 1:
        if not mpi_Command:
            raise RuntimeError , 'could not find an mpi interface'

        if 'SU2_DEF' in the_Command:
            trun = '0-00:05' # 20 seconds on 32 cores on Sherlock
        elif 'SU2_CFD' in the_Command:
            #trun = '0-01:15' # 45 minutes on 32 cores on Sherlock (3D RANS)
            trun = '0-00:30' # 2 minutes on 32 cores on Sherlock (3D Euler)
        elif 'SU2_DOT' in the_Command:
            trun = '0-00:15' # not timed yet
        elif 'SU2_AD' in the_Command:
            trun = '0-01:15' # not timed yet
        else:
            trun = '0-00:30'
            
        the_Command = mpi_Command % (processes, trun, the_Command)
    return the_Command

def run_command( Command ):
    """ runs os command with subprocess
        checks for errors from command
    """
    
    sys.stdout.flush()
    
    # For debugging record environment variables
    if 'SU2_DEF' in Command:
        getAndWriteSlurmVariables('SU2_DEF')
    elif 'SU2_CFD' in Command:
        getAndWriteSlurmVariables('SU2_CFD')
    
    print("Running command: %s" % Command)
    proc = subprocess.Popen( Command, shell=True    ,
                             stdout=sys.stdout      , 
                             stderr=subprocess.STDOUT ,
                             bufsize=-1  )
    return_code = proc.wait()
    #message = proc.stderr.read()
    message = 'Message is unavailable'

    # Rerun command if it appears that the correct file was not written
    if return_code > 0: #('SU2_DEF' in Command and not os.path.exists('nozzle.su2')) or ('SU2_CFD' in Command and not os.path.exists('nozzle.dat')):
        print("Rerunning command: %s" % Command)
        proc = subprocess.Popen( Command, shell=True    ,
                                 stdout=sys.stdout      ,
                                 stderr=subprocess.STDOUT ,
                                 bufsize=-1  )
        return_code = proc.wait()
        #message = proc.stderr.read() 
        message = '2nd message is unavailable'
    
#    if return_code < 0:
#        message = "SU2 process was terminated by signal '%s'\n%s" % (-return_code,message)
#        raise SystemExit , message
#    elif return_code > 0:
#        message = "Path = %s\nCommand = %s\nSU2 process returned error '%s'\n%s" % (os.path.abspath(','),Command,return_code,message)
#        if return_code in return_code_map.keys():
#            exception = return_code_map[return_code]
#        else:
#            exception = RuntimeError
#        raise exception , message
#    else:
#        sys.stdout.write(message)
            
    return return_code

