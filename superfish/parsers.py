import numpy as np
import os

def parse_automesh(file):
    if os.path.exists(file):
        lines = open(file, 'r').readlines()
    return lines


def parse_sfo(filename, verbose=False):
    """
    Master parser for the SFO file.
    
    Returns the output dict. 
    
    """
    
    groups = parse_sfo_into_groups(filename)
    
    
    d = {
        'wall_segments':[],
        'other':{}
    }
    segments = []
    
    for g in groups:
        dat = process_group(g, verbose=verbose) 
        type = dat['type']
        
        if type == 'wall_segment':
            d['wall_segments'].append(dat)
        elif type in ['summary']:
            d[type] = dat
        else:
            d['other'][type] = dat
            
    return d
    
  


def parse_sfo_into_groups(filename):
    """
    Parses SFO file into groups according to separator:
    '-------------------------------------------------------------------------------'
    
    Returns a list of dicts, with:
        raw_type: the first line
        lines: list of lines
    
    """
    groups = []
    
    
    
    sep = '-------------------------------------------------------------------------------'
    
    with open(filename, 'r') as f:
        line = f.readline()
        g = {'raw_type':'header', 'lines':[line]}
        groups = [g]
        while line:
            line = line.strip()
            if line == sep:
                # New group in next line, skipping empty
                gname = f.readline().strip()
                while not gname:
                    gname = f.readline().strip()
                                   
                g = {'raw_type': gname, 'lines':[]}   
                groups.append(g)          
            else:
                # regular line
                g['lines'].append(line)
            
            line = f.readline()
    return groups


def process_group(group, verbose=False):
    """
    processes a single output group dict into usable data.
    """
    
    rtype = group['raw_type']
    lines = group['lines']

    d = {}
    
    if rtype.startswith('All calculated values below refer to the mesh geometry only'):
        d['type'] = 'summary'
        d['data'], d['units'] = parse_sfo_summary_group(lines)
    elif rtype.startswith('Power and fields on wall segment'):
        d['type'] = 'wall_segment'
        line1 = rtype # This should be parsed fully
        
        d['data'] = parse_sfo_segment([line1]+lines)
        
        
    else:
        # No parser yet:
        if verbose:
            print('No parser for:', rtype)
        
        d['type'] = rtype
        d['lines'] = lines
    
    return d



#_________________________________
# Individual parsers


def parse_wall_segment_line1(line):
    """
    helper parse_sfo_segment
    """
    d = {}
    ix, x = line.split('segment')[1].split(' K,L =')
    d['segment_number'] = int(float((ix)))
    kl0, kl1 = x.split('to')
    k0, l0 = kl0.split(',')
    d['K_beg'], d['L_beg'] = int(k0), int(l0)
    k1, l1 = kl1.split(',')
    d['K_end'], d['L_end'] = int(k1), int(l1)    
    return d


def parse_sfo_segment(lines):
    """
    Parses lines that start with:
        'Power and fields on wall segment'
    """
    
    # key = value lines
    
    info = parse_wall_segment_line1(lines[0])
    
    M = "                      (cm)          (cm)         (A/m)       (V/m)"
    inside = False
    
    dats = []
    
    for L in lines[1:]:
        L = L.strip()
        
        # Look for key=value
        if '=' in L:
            key, val = L.split('=')
            info[key] = val
            continue
        
        if L == M.strip():
            inside = True
            dat = {'Z':[], 'R':[], 'H':[], 'E':[]}
            dats.append(dat)
            continue
        if not inside:
            continue
        
        x = L.split()
        if len(x) == 7:
            x = x[3:]
        
        if len(x) == 4:
            dat['Z'].append(float(x[0]))
            dat['R'].append(float(x[1])) 
            dat['H'].append(float(x[2]))   
            dat['E'].append(float(x[3]))
        else:
            # Exiting
            for k, v in dat.items():
                dat[k] = np.array(v)
            
            inside=False
            

            
    return {'wall':dats, 'info':info}
    



def parse_sfo_summary_group(lines): 
    """
    
    
    """
    
    
    dict_vals = {}
    dict_units = {}
    for s in lines:
        if s == "":
            break
        else:
            list = s.split("=")
            # split using ","
            results = list[-1].split(",")
            key = "".join(list[0:-1])
            # case 1: only one out put, dict reference to a single value/ unit
            if len(results) == 1:
                s = results[0]
                s = s.strip()
                s = s.split(" ")
                if len(s) == 1:
                    val = s[0]
                    unit = ""
                else:
                    val = s[0]
                    unit = s[1]
                val = float(val)
                dict_vals.update({key: val})
                dict_units.update({key: unit})
            # case 2: multiple outputs, dict reference to list of values/units
            else:
                vals = []
                units = []
                for s in results:
                    s = s.strip()
                    s = s.split(" ")
                    if len(s) == 1:
                        val = s[0]
                        unit = ""
                    else:
                        val = s[0]
                        unit = s[1]
                    val = float(val)
                    vals.append(val)
                    units.append(unit)
                dict_vals.update({key: vals})
                dict_units.update({key: units})
    return dict_vals, dict_units

