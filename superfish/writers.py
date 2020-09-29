import numpy as np

def fish_externalfield_data(t7data,
                      eleAnchorPt = 'beginning',
                      fieldScale = 1,
                      RFphase = 0,
                      zmin = 0,
                      name = None
                      ):
    """
    Input: 
        t7data dict from a parsed T7 file. This is in the native Superfish units. 
    
    Superfish fields oscillate as:
        Er, Ez ~ cos(wt)
        Hphi   ~ -sin(wt)
     
    
    For complex fields oscillating as e^-iwt
    
        Re(Ex*e^-iwt)   ~ cos
        Re(-iB*e^-iwt) ~ -sin        
    and therefore B = -i * mu_0 * H_phi is the complex magnetic field in Tesla
    
    Output:
        attrs, components
        
    that are ready to be written to an HDF5 file. 
        
    
    """
    
    attrs = {}
    
    # Set requested zmin
    attrs['gridOriginOffset'] = (0, 0, zmin)
    
    # Use these to calculate spacing
    zmin = t7data['xmin']*.01
    zmax = t7data['xmax']*.01
    rmin = t7data['ymin']*.01
    rmax = t7data['ymax']*.01
    
    assert rmin == 0, f'rmin is not zero: {rmin}'
    
    nr = t7data['ny']
    nz = t7data['nx']
    
    dz = (zmax-zmin)/(nz-1)
    dr = (rmax)/(nr-1)
    
    attrs['gridGeometry'] = 'cylindrical'
    attrs['gridLowerBound'] = (0, 1, 0)
    
    attrs['gridSpacing'] = (dr, 0, dz)
    attrs['fundamentalFrequency'] = t7data['freq']*1e6
    
    attrs['masterParameter'] = 'VOLTAGE'
    
    attrs['harmonic'] = 1
    attrs['RFphase'] = RFphase
    
    if name:
        attrs['name'] = name     
            
    # Normalize on-axis field        
    Ez0_max = np.abs(t7data['Ez'][0,:]).max()            
        
    components = {}
    components['Er'] = t7data['Er'].reshape(nr, 1, nz) * 1e6/Ez0_max
    components['Ez'] = t7data['Ez'].reshape(nr, 1, nz) * 1e6/Ez0_max
    components['Btheta'] = t7data['Hphi'].reshape(nr, 1, nz) * -4e-7j*np.pi/Ez0_max # -i * mu_0
    
    
    