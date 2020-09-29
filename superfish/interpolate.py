from superfish.parsers import parse_t7

import numpy as np

from glob import glob
import os


def get_t7(path):
    """
    Returns a list of T7 files in path
    """
    return glob(os.path.join(path, '*T7'))


def interpolate2d(sf,
                  xmin=-1000, xmax=1000, nx=100,
                  ymin=0, ymax=0, ny=1,
                  labels=['Ez', 'Er', 'E', 'Hphi']):
    """
    
    Runs SF7.EXE on a Superfish object sf, requesting interpolating data, and reads the Parmela T7 file. 
    
    Dimensions are in cm.
    
    Labels will label the output columns. The user must know what these are from the problem.
    
    TODO: detect these from SF object
    
    SF7 automatically adjusts the bounds if they are requested outside of the computational domain.
    
    Returns a dict with:
        xmin
        xmax
        nx
        ymin
        ymax
        ny
        freq: frequency in MHz
        data: 2D array of shape (nx, ny)
    
    
    """
    
    # The interpolation grid
    F=f"""Parmela
{xmin} {ymin} {xmax} {ymax}
{nx-1} {ny-1}
End"""
    # Clear old T7
    for f in get_t7(sf.path):
        os.remove(f)
    
    # Write 
    ifile = sf.basename+'.IN7'
    with open(os.path.join(sf.path, ifile), 'w') as f:
        f.write(F)
    
    # Run
    sf.run_cmd('sf7', ifile)
    
    # Get the filename
    t7file = get_t7(sf.path)
    assert len(t7file) == 1
    t7file = t7file[0]
    
    d =  parse_t7(t7file, labels=labels)
    
    return d