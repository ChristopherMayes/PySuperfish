from superfish.parsers import parse_fish_t7, parse_poisson_t7

from pmd_beamphysics import FieldMesh

import numpy as np

from glob import glob
import os
import re


def get_t7(path):
    """
    Returns a list of T7 files in path
    """
    return glob(os.path.join(path, '*T7'))


def interpolate2d(sf,
                  zmin=None, zmax=None, nz=None,
                  rmin=None, rmax=None, nr=None,
                  xmin=None, xmax=None, nx=None,
                  ymin=None, ymax=None, ny=None,
                  return_fieldmesh=False):
    """
    
    Runs SF7.EXE on a Superfish object sf, requesting interpolating data, and reads the Parmela T7 file. 
    
    Units are in the input units of the program. 
    
    Labels will label the output columns. The user must know what these are from the problem.
    
    TODO: detect these from SF object
    
    SF7 automatically adjusts the bounds if they are requested outside of the computational domain.
    
    # TODO write up the return
    """

    if sf.geometry == 'cylindrical':

        assert xmin is None, f'Input parameter xmin inconsistent with {sf.geometry} geometry'
        assert xmax is None, f'Input parameters xmax inconsistent with {sf.geometry} geometry'
        assert nx is None, f'Input parameters nx inconsistent with {sf.geometry} geometry'

        assert ymin is None, f'Input parameter ymin inconsistent with {sf.geometry} geometry'
        assert ymax is None, f'Input parameters ymax inconsistent with {sf.geometry} geometry'
        assert ny is None, f'Input parameters ny inconsistent with {sf.geometry} geometry'

        return interpolate_cylindrical(sf,
                                       zmin=zmin, zmax=zmax, nz=nz,
                                       rmin=rmin, rmax=rmax, nr=nr, 
                                       return_fieldmesh=return_fieldmesh)
        
        
    elif sf.geometry == 'rectangular':

        assert rmin is None, f'Input parameter rmin inconsistent with {sf.geometry} geometry'
        assert rmax is None, f'Input parameters rmax inconsistent with {sf.geometry} geometry'
        assert nr is None, f'Input parameters nr inconsistent with {sf.geometry} geometry'

        assert zmin is None, f'Input parameter zmin inconsistent with {sf.geometry} geometry'
        assert zmax is None, f'Input parameters zmax inconsistent with {sf.geometry} geometry'
        assert nz is None, f'Input parameters nz inconsistent with {sf.geometry} geometry'

        return interpolate_xy(sf, 
                              xmin=xmin, xmax=xmax, nx=nx,
                              ymin=ymin, ymax=ymax, ny=ny,
                              return_fieldmesh=return_fieldmesh)        
    

def interpolate_xy(sf, 
                   xmin=-1000, xmax=1000, nx=100,
                   ymin=-1000, ymax=1000, ny=200,
                   return_fieldmesh=False):

    assert xmin is not None and xmax is not None and nx is not None
    assert ymin is not None and ymax is not None and ny is not None

    problem = sf.problem 
    
    # fish and poisson have the opposite conventions:
    if problem == 'fish':
    # The interpolation grid
        F=f"""
{xmin} {ymin} {xmax} {ymax}
{nx-1} {ny-1}
End"""
        
    elif problem == 'poisson':
        F=f"""Grid
{xmin} {ymin} {xmax} {ymax}
{nx-1} {ny-1}
End"""
    else:
        raise ValueError(f'unknowm problem: {problem}')
    

    # Clear old T7
    for f in get_t7(sf.path):
        os.remove(f)
    
    # Write 
    ifile = sf.basename+'.IN7'
    with open(os.path.join(sf.path, ifile), 'w') as f:
        f.write(F)
    
    # Needed so that the fields aren't normalized to 1 MV/m average
    inifile = os.path.join(sf.path, 'SF.INI')
    with open(inifile, 'w') as f:
        f.write("""[global]
Force1MVperMeter=No""")

    # Needed on WSL, otherwise optional
    t35file = sf.basename+'.T35'
    
        
    # Run
    sf.run_cmd('sf7', ifile, t35file)

    outsf7_file = os.path.join(sf.path, 'OUTSF7.txt')

    with open(outsf7_file, 'r') as fid:
        sf7_text = fid.read()

    lines = sf7_text.split('\n')

    xmin, ymin, xmax, ymax, x_inc, y_inc = None, None, None, None, None, None

    for ii, line in enumerate(lines):

        if line.strip().startswith('(Xmin,Ymin)'):
            min_tokens = line.split('=')[1].replace('(', '').replace(')', '').split(',')
            xmin, ymin = float(min_tokens[0]), float(min_tokens[1])

        if line.strip().startswith('(Xmax,Ymax)'):
            max_tokens = line.split('=')[1].replace('(', '').replace(')', '').split(',')
            xmax, ymax = float(max_tokens[0]), float(max_tokens[1])

        if line.strip().startswith('X and Y increments:'):
            inc_tokens = line.split(':')[1].split()
            x_inc, y_inc = int(inc_tokens[0]), int(inc_tokens[1])

            index = ii
            break

    #print(x_inc+1, y_inc+1)
    
    columns = lines[index+2].split()
    units = [u.replace('(', '').replace(')', '') for u in lines[index+3].split()]

    if 'Ex' in columns and 'Ey' in columns:
        field_x_str = 'Ex'
        field_y_str = 'Ey'
        
    elif 'Bx' in columns and 'By' in columns:
        field_x_str = 'Bx'
        field_y_str = 'By'
    else:
        raise ValueError('Unknown fields')
        

    data = np.loadtxt(outsf7_file, comments='#', skiprows=index+4)

    nx, ny = x_inc+1, y_inc+1

    field_x = data[:, columns.index(field_x_str)].reshape(nx, ny, order='F')
    field_y = data[:, columns.index(field_y_str)].reshape(nx, ny, order='F')

    dat = {'geometry': sf.geometry, 'problem': sf.problem, 
           'xmin': xmin, 'xmax': xmax, 'nx': x_inc+1, field_x_str: field_x,
           'ymin': ymin, 'ymax': ymax, 'ny': y_inc+1, field_y_str: field_y,
           'units': {columns[ii]: units[ii] for ii in range(len(columns)) }}

    return dat

    """
    # Get the filename
    t7file = get_t7(sf.path)
    assert len(t7file) == 1, f'T7 file is missing.'
    t7file = t7file[0]
    
    
    # Optional fieldmesh parsing
    if return_fieldmesh:
        # Parsing is different for each:
        if problem == 'fish':
            type = 'electric'
            return FieldMesh.from_superfish(t7file)
        else:
            if sf.output['sfo']['header']['variable']['XJFACT'] == 0:
                type = 'electric'
            else:
                type = 'magnetic'
            return FieldMesh.from_superfish(t7file, type=type)
        
        
    
    # Parsing is different for each:
    if problem == 'fish':
        type = 'electric'
        d =  parse_fish_t7(t7file)
    else:
        if sf.output['sfo']['header']['variable']['XJFACT'] == 0:
            type = 'electric'
        else:
            type = 'magnetic'
        d =  parse_poisson_t7(t7file, 'cylindrical', type=type)
    
    return d
    """

def interpolate_cylindrical(sf,
                  zmin=-1000, zmax=1000, nz=100,
                  rmin=0, rmax=0, nr=1, return_fieldmesh=False):
    """
    
    Runs SF7.EXE on a Superfish object sf, requesting interpolating data, and reads the Parmela T7 file. 
    
    Units are in the input units of the program. 
    
    Labels will label the output columns. The user must know what these are from the problem.
    
    TODO: detect these from SF object
    
    SF7 automatically adjusts the bounds if they are requested outside of the computational domain.
    
    Returns a dict with:
        rmin: minimum radius in cm
        rmax: maximum radius in cm
        nr:   number of radius points
        zmin: minimum z in cm
        zmax: maximum z in cm
        nz:   number of z points
        freq: frequency in MHz
        data: 2D array of shape (nr, nz)
    
    
    """

    assert zmin is not None and zmax is not None and nz is not None
    assert rmin is not None and rmax is not None and nr is not None
    
    problem = sf.problem 
    
    # fish and poisson have the opposite conventions:
    if problem == 'fish':
    # The interpolation grid
        F=f"""Parmela
{zmin} {rmin} {zmax} {rmax}
{nz-1} {nr-1}
End"""
        
    elif problem == 'poisson':
        F=f"""Parmela
{rmin} {zmin} {rmax} {zmax}
{nr-1} {nz-1}
End"""
    else:
        raise ValueError(f'unknowm problem: {problem}')
    

    # Clear old T7
    for f in get_t7(sf.path):
        os.remove(f)
    
    # Write 
    ifile = sf.basename+'.IN7'
    with open(os.path.join(sf.path, ifile), 'w') as f:
        f.write(F)
    
    # Needed so that the fields aren't normalized to 1 MV/m average
    inifile = os.path.join(sf.path, 'SF.INI')
    with open(inifile, 'w') as f:
        f.write("""[global]
Force1MVperMeter=No""")

    # Needed on WSL, otherwise optional
    t35file = sf.basename+'.T35'
    
        
    # Run
    sf.run_cmd('sf7', ifile, t35file)
    
    # Get the filename
    t7file = get_t7(sf.path)
    assert len(t7file) == 1, f'T7 file is missing.'
    t7file = t7file[0]
    
    
    # Optional fieldmesh parsing
    if return_fieldmesh:
        # Parsing is different for each:
        if problem == 'fish':
            type = 'electric'
            return FieldMesh.from_superfish(t7file)
        else:
            if sf.output['sfo']['header']['variable']['XJFACT'] == 0:
                type = 'electric'
            else:
                type = 'magnetic'
            return FieldMesh.from_superfish(t7file, type=type)
        
        
    
    # Parsing is different for each:
    if problem == 'fish':
        type = 'electric'
        d =  parse_fish_t7(t7file)
    else:
        if sf.output['sfo']['header']['variable']['XJFACT'] == 0:
            type = 'electric'
        else:
            type = 'magnetic'
        d =  parse_poisson_t7(t7file, 'cylindrical', type=type)

    return d

    
