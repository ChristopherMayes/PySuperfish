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
    attrs['eleAnchorPt'] = eleAnchorPt
    
    # Set requested zmin
    attrs['gridOriginOffset'] = (0, 0, zmin)
    
    # Use these to calculate spacing
    zmin = t7data['zmin']*.01
    zmax = t7data['zmax']*.01
    rmin = t7data['rmin']*.01
    rmax = t7data['rmax']*.01
    
    assert rmin == 0, f'rmin is not zero: {rmin}'
    
    nr = t7data['nr']
    nz = t7data['nz']
    
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
    Ez0_max = 1e6*np.abs(t7data['Ez'][0,:]).max() # V/m
        
    components = {}
    components['Er'] = t7data['Er'].reshape(nr, 1, nz) * 1e6/Ez0_max 
    components['Ez'] = t7data['Ez'].reshape(nr, 1, nz) * 1e6/Ez0_max
    components['Btheta'] = t7data['Hphi'].reshape(nr, 1, nz) * -4e-7j*np.pi/Ez0_max # -i * mu_0
    
    return attrs, components



def poisson_externalfield_data(t7data,
                      eleAnchorPt = 'beginning',
                      fieldScale = 1,
                      type='electric',
                      zmin = 0,
                      name = None
                      ):
    """
    Input: 
        t7data dict from a parsed T7 file. This is in the native Superfish units. 
    
    Output:
        attrs, components
        
    that are ready to be written to an HDF5 file. 
        
    
    """
    
    attrs = {}
    attrs['eleAnchorPt'] = eleAnchorPt
    
    # Set requested zmin
    attrs['gridOriginOffset'] = (0, 0, zmin)
    
    # Use these to calculate spacing
    zmin = t7data['zmin']*.01
    zmax = t7data['zmax']*.01
    rmin = t7data['rmin']*.01
    rmax = t7data['rmax']*.01
    
    assert rmin == 0, f'rmin is not zero: {rmin}'
    
    nr = t7data['nr']
    nz = t7data['nz']
    
    dz = (zmax-zmin)/(nz-1)
    dr = (rmax)/(nr-1)
    
    attrs['gridGeometry'] = 'cylindrical'
    attrs['gridLowerBound'] = (0, 1, 0)
    
    attrs['gridSpacing'] = (dr, 0, dz)
    attrs['fundamentalFrequency'] = 0
    
    attrs['harmonic'] = 0
    
    if name:
        attrs['name'] = name     
            
    if type=='electric':
        fr = 'Er'
        fz = 'Ez'  
        attrs['masterParameter'] = 'VOLTAGE'
        
    elif type=='magnetic':
        fr = 'Br'
        fz = 'Bz' 
        attrs['masterParameter'] = 'BS_FIELD'
            
    # Normalize on-axis field        
    fz0_max = np.abs(t7data[fz][0,:]).max()            
        
    components = {}
    components[fr] = t7data[fr].reshape(nr, 1, nz) /fz0_max
    components[fz] = t7data[fz].reshape(nr, 1, nz) /fz0_max    

    return attrs, components
    
    
    