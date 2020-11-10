import numpy as np
import scipy.constants
mu_0 = scipy.constants.mu_0

def fish_externalfield_data(t7data,
                      eleAnchorPt = 'beginning',
                      fieldScale = 1,
                      RFphase = 0,
                      z_offset = 0,
                      name = None,
                      normalize_by_Ez0=False
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
        dict with dicts:
            attrs
            components
            
    that are ready to be written to an HDF5 file. 
        
    
    """
    
    attrs = {}
    attrs['eleAnchorPt'] = eleAnchorPt
    
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
    attrs['axisLabels'] = ('r', 'theta', 'z')
    attrs['gridLowerBound'] = (0, 1, 0)
    attrs['gridSize'] = (nr, 1, nz)        
    attrs['gridSpacing'] = (dr, 0, dz)
    
    # Set requested zmin
    attrs['gridOriginOffset'] = (0, 0, zmin+z_offset)
    
    attrs['fundamentalFrequency'] = t7data['freq']*1e6
    
    # Bmad non-standard
    ## attrs['masterParameter'] = 'VOLTAGE'
    
    attrs['harmonic'] = 1
    attrs['RFphase'] = RFphase
    
    if name:
        attrs['name'] = name     
            
    # Normalize on-axis field
    if normalize_by_Ez0:
        Ez0_max = 1e6*np.abs(t7data['Ez'][0,:]).max() # V/m
    else:
        Ez0_max = 1
        
    components = {}
    components['electricField/r'] = t7data['Er'].reshape(nr, 1, nz).astype(np.complex) * 1e6/Ez0_max
    components['electricField/z'] = t7data['Ez'].reshape(nr, 1, nz).astype(np.complex) * 1e6/Ez0_max
    components['magneticField/theta'] = t7data['Hphi'].reshape(nr, 1, nz) * -1j*mu_0/Ez0_max # -i * mu_0
    
    
    
    return dict(attrs=attrs, components=components)



def poisson_externalfield_data(t7data,
                      eleAnchorPt = 'beginning',
                      fieldScale = 1,
                      type='electric',
                      z_offset=0,
                      name = None,
                      normalize_by_fz0=False                               
                      ):
    """
    Input: 
        t7data dict from a parsed T7 file. This is in the native Superfish units. 
    
    Output:
        dict with dicts:
            attrs
            components
        
    that are ready to be written to an HDF5 file. 
        
    
    """
    
    attrs = {}
    
    assert eleAnchorPt in ['beginning', 'center', 'end'], f'Unallowed eleAnchorPt point: {eleAnchorPt}'
    
    attrs['eleAnchorPt'] = eleAnchorPt
        
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
    attrs['axisLabels'] = ('r', 'theta', 'z')
    attrs['gridLowerBound'] = (0, 1, 0)
    attrs['gridSize'] = (nr, 1, nz)        
    attrs['gridSpacing'] = (dr, 0, dz)
    
    # Set requested zmin
    attrs['gridOriginOffset'] = (0, 0, zmin+z_offset)    
    
    attrs['fundamentalFrequency'] = 0
    attrs['harmonic'] = 0
    
    if name:
        attrs['name'] = name     
            
    if type=='electric':
        fr = 'Er'
        fz = 'Ez'  
        ofr = 'electricField/r' # Ouptut names
        ofz = 'electricField/z'
        attrs['masterParameter'] = 'VOLTAGE'
        
    elif type=='magnetic':
        fr = 'Br'
        fz = 'Bz' 
        ofr = 'magneticField/r'
        ofz = 'magneticField/z'
        # Bmad non-standard
        ## attrs['masterParameter'] = 'BS_FIELD'
            
    # Normalize on-axis field     
    if normalize_by_fz0:
        fz0_max = np.abs(t7data[fz][0,:]).max()            
    else:
        fz0_max = 1
        
    components = {}
    components[ofr] = t7data[fr].reshape(nr, 1, nz) /fz0_max
    components[ofz] = t7data[fz].reshape(nr, 1, nz) /fz0_max    

    return dict(attrs=attrs, components=components)
    

def write_fish_t7(filename, t7data,  fmt='%10.8e'):
    """
    Writes a T7 file from FISH t7data dict. 
    
    
    See:
        superfish.parsers.parse_fish_t7
    """
    
    # Collect these
    xmin = t7data['zmin']
    xmax = t7data['zmax']
    nx   = t7data['nz']
    ymin = t7data['rmin']
    ymax = t7data['rmax']
    ny   = t7data['nr']
    freq = t7data['freq']
    
    
    header = f"""{xmin} {xmax} {nx-1}
{freq}
{ymin} {ymax} {ny-1}"""
    
    
    # Unroll the arrays
    dat = np.array([t7data[f].reshape(nx*ny).T for f in ['Ez', 'Er', 'E', 'Hphi']]).T
    
    np.savetxt(filename, dat, header=header, comments='',  fmt = fmt)
    
    return filename

def write_poisson_t7(filename, t7data,  fmt='%10.8e'):
    """
    Writes a T7 file from POISSON t7data dict. 
    
    
    See:
        superfish.parsers.parse_poisson_t7
    """
    
    # Collect these
    ymin = t7data['zmin']
    ymax = t7data['zmax']
    ny   = t7data['nz']
    xmin = t7data['rmin']
    xmax = t7data['rmax']
    nx   = t7data['nr']
    #freq = t7data['freq']
    
    
    header = f"""{xmin} {xmax} {nx-1}
{ymin} {ymax} {ny-1}"""
    
    
    if 'Ez' in t7data:
        keys = ['Er', 'Ez']
    else:
        keys = ['Br', 'Bz']
    
    # Unroll the arrays
    dat = np.array([t7data[f].reshape(nx*ny, order='F').T for f in keys]).T
    
    np.savetxt(filename, dat, header=header, comments='',  fmt = fmt)
    
    return filename