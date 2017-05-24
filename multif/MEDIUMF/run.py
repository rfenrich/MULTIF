from .. import SU2
from meshgeneration import *
from runSU2 import *
import SU2postprocessing
import AEROSpostprocessing

from .. import nozzle as nozzlemod

try:
    from runAEROS import *
except ImportError:
    print 'Error importing all functions from runAEROS.\n'

#def CheckOptions (nozzle):
    
#		print "Check options"
    #if nozzle.Dim == 3 :
    #    sys.stderr.write("\n  ## ERROR : Only 2D axisymmetric simulations are available for now.\n\n");
    #    sys.exit(0);
    
    #if nozzle.method == 'RANS':
    #    sys.stderr.write("\n  ## ERROR : Only Euler simulations are available for now.\n\n");
    #    sys.exit(0);
    

def Run( nozzle, output = 'verbose', writeToFile=1 ):

    # Obtain mass and volume
    if 'MASS' in nozzle.responses or 'VOLUME' in nozzle.responses:
        volume, mass = nozzlemod.geometry.calcVolumeAndMass(nozzle)
        if 'MASS' in nozzle.responses:
            nozzle.responses['MASS'] = np.sum(mass)
            #nozzle.mass = np.sum(mass)
        if 'VOLUME' in nozzle.responses:
            nozzle.responses['VOLUME'] = np.sum(volume)
            #nozzle.volume = np.sum(volume)
        
    # Calculate mass gradients if necessary
    if 'MASS' in nozzle.gradients and nozzle.gradients['MASS'] is not None:
        if ( nozzle.gradients_method == 'ADJOINT' ):
            # Convergence study using B-spline coefs show finite difference mass gradients
            # converge. Most accurate gradients use absolute step size 1e-8. RWF 5/10/17
            nozzle.gradients['MASS'] = nozzlemod.geometry.calcMassGradientsFD(nozzle,1e-8);
        elif ( nozzle.gradients_method == 'FINITE_DIFF' ):
            nozzle.gradients['MASS'] = nozzlemod.geometry.calcMassGradientsFD(\
              nozzle,nozzle.fd_step_size);
        else:
		    sys.stderr.write('  ## ERROR : Unknown gradients computation '
		      'method.\n');
		    sys.exit(1);
	
	# Calculate volume gradients if necessary
    if 'VOLUME' in nozzle.gradients and nozzle.gradients['VOLUME'] is not None:
        sys.stderr.write('\n ## ERROR : gradients for VOLUME are not supported\n\n');
        sys.exit(1);
        
    # Obtain mass of wall and gradients only if requested
    if 'MASS_WALL_ONLY' in nozzle.responses:
        n_layers = len(nozzle.wall.layer);
        nozzle.responses['MASS_WALL_ONLY'] = np.sum(performanceTuple[1][:n_layers]);
        
    if 'MASS_WALL_ONLY' in nozzle.gradients and nozzle.gradients['MASS_WALL_ONLY'] is not None:
        sys.stderr.write('\n ## ERROR : gradients for MASS_WALL_ONLY are not supported\n\n');
        sys.exit(1);

    # Run aero-thermal-structural analysis if necessary
    runAeroThermalStructuralProblem = 0;
    for k in nozzle.responses:
        if k not in ['MASS','VOLUME','MASS_WALL_ONLY']:
            runAeroThermalStructuralProblem = 1;    
    
    # Run aero-thermal-structural gradient analysis if necessary
    if nozzle.output_gradients == 1:
        runAeroThermalStructuralGradients = 0;        
        for k in nozzle.gradients:
            if k not in ['MASS','VOLUME','MASS_WALL_ONLY']:
                if nozzle.gradients[k] is not None:
                    runAeroThermalStructuralGradients = 1;
    
    if runAeroThermalStructuralProblem:
        
        # Run aero analysis (and thrust adjoint if necessary)  
        CheckSU2Version(nozzle);	
	    #CheckOptions (nozzle);
        curDir = os.path.dirname(os.path.realpath(__file__));	
        if nozzle.runDir != '':
	        os.chdir(nozzle.runDir);	
        gradCalc = runSU2 (nozzle);
	
	    # Run thermal/structural analyses
        if nozzle.thermalFlag == 1 or nozzle.structuralFlag == 1:
	        runAEROS(nozzle, output);
	        
        # Assign aero QoI if required
        SU2postprocessing.PostProcess(nozzle, output);
        
        # Assign thermal/structural QoI if required
        if nozzle.thermalFlag == 1 or nozzle.structuralFlag == 1:
            AEROSpostprocessing.PostProcess(nozzle, output);             
        
        # Calculate gradients if necessary
        if nozzle.output_gradients == 1 and runAeroThermalStructuralGradients:
        
            if ( nozzle.gradients_method == 'ADJOINT' ):
                if gradCalc == 0: # i.e. failed adjoint calculation, use finite differences
                    multif.gradients.calcGradientsFD(nozzle,nozzle.fd_step_size,output);
                else:
                    # Check for other required gradients
                    otherRequiredGradients = 0;
                    for k in nozzle.gradients:
                        if k not in ['MASS','VOLUME','MASS_WALL_ONLY','THRUST']:
                            otherRequiredGradients = 1;
                            sys.stderr.write(' ## WARNING: QoI gradients desired using ADJOINT '
                              'method which do not have an associated adjoint calculation.\n'
                              ' Namely: %s. The current implementation requires finite '
                              'differencing across the aero analysis, so this method is '
                              'equivalent in computational cost to choosing the FINITE_DIFF'
                              ' method\n' % k);
                    # Do finite difference for other QoI if there are any, but use
                    # adjoint gradients for thrust
                    if otherRequiredGradients:
                        saveThrustGradients = nozzle.gradients['THRUST'];
                        nozzle.gradients['THRUST'] = None;
                        multif.gradients.calcGradientsFD(nozzle,nozzle.fd_step_size,output);
                        nozzle.gradients['THRUST'] = saveThrustGradients;
                        
            elif ( nozzle.gradients_method == 'FINITE_DIFF' ):
            
                multif.gradients.calcGradientsFD(nozzle,nozzle.fd_step_size,output);  
                         
            else:
			    sys.stderr.write('  ## ERROR : Unknown gradients computation '
			      'method.\n');
			    sys.exit(1);
			    
			# Write separate gradients file
            gradFile = open(nozzle.output_gradients_filename,'w');
            for k in nozzle.outputTags:
			    np.savetxt(gradFile,nozzle.gradients[k]);
            gradFile.close();   			
        
    # Write data
    if writeToFile:
        if nozzle.outputFormat == 'PLAIN':
            nozzle.WriteOutputFunctions_Plain();
        else:
            nozzle.WriteOutputFunctions_Dakota();
        
    return 0;
