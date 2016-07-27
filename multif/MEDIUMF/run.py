from .. import SU2
from meshgeneration import *
from runSU2 import *
from runAEROS import *
from postprocessing import *


def CheckOptions (nozzle):
	
	if nozzle.Dim == 3 :
		sys.stderr.write("\n  ## ERROR : Only 2D axisymmetric simulations are available for now.\n\n");
		sys.exit(0);
	
	if nozzle.method == 'RANS':
		sys.stderr.write("\n  ## ERROR : Only Euler simulations are available for now.\n\n");
		sys.exit(0);
	

def Run( nozzle ):
	
	# --- Check SU2 version
	
	CheckSU2Version(nozzle);

	# --- Check fidelity level
	
	CheckOptions (nozzle);
	
	curDir = os.path.dirname(os.path.realpath(__file__));
	nozzle.runDir = curDir; # RWF 7/27/16

	#os.chdir(nozzle.runDir); # RWF 7/27/16
	
	
	# --- Run CFD
	
	runSU2 (nozzle);
	
	# --- Run AEROS
	
	runAEROS (nozzle);
	
	# --- Postprocessing
	
	PostProcessing(nozzle);
	
	sys.stdout.write("\n  -- Info : Result directory :  %s\n\n" % nozzle.runDir);
	
	
