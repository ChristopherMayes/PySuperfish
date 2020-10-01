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
        elif type in ['summary','BeamEnergy']:
            d[type] = dat
        elif type == 'header':
            d['header'] = parse_header_lines(dat['lines'])
        
        else:
            d['other'][type] = dat
            
    # update Kinetic energy in 'summary' with the right value
    if 'summary' in d and 'BeamEnergy' in d:
        d['summary']['data']['kinetic_energy'] = d['BeamEnergy']['data']['BeamEnergy']/1e6
        d['summary']['units']['kinetic_energy'] = 'MeV'

    return d




def parse_sfo_into_groups(filename):
    """
    Parses SFO file into groups according to separator that starts with:
    '-------------------'

    Returns a list of dicts, with:
        raw_type: the first line
        lines: list of lines

    """

        
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    groups = []

    sep = '-------------------'
    
    
    g = {'raw_type':'header', 'lines':[]}
    groups = [g]
    
    new_group = False
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Look for new group    
        if line.startswith(sep):
            new_group = True
            continue
        
        # Check for new group
        if new_group:
            gname = line
            new_group = False
            g = {'raw_type': gname, 'lines':[]}
            groups.append(g)
            continue
            
        # regular line
        g['lines'].append(line)

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
    elif rtype.startswith('Power and fields on wall segment') or rtype.startswith('Fields on segment'):
        d['type'] = 'wall_segment'
        line1 = rtype # This should be parsed fully

        d.update(parse_sfo_segment([line1]+lines))
    elif rtype.startswith('The field normalization factor ASCALE for this problem is based'):
        d['type'] = 'BeamEnergy'
        d['data'], d['units'] = parse_sfo_beam_energy(lines)

    else:
        # No parser yet:
        if verbose:
            print('No parser for:', rtype)

        d['type'] = rtype
        d['lines'] = lines

    return d



#_________________________________
# T7 files

def parse_fish_t7(t7file, geometry='cylindrical'):
    """
    Parses a T7 file. The T7 header should have:
    
    xmin(cm), xmax(cm), nx-1
    freq(MHz)
    ymin(cm), ymax(cm), ny-1
    4 columns of data: Ez, Er, E, Hphi
    
    TODO: Poisson problems, detect rectangular or cylindrical coordinates
    
    Returns a dict with:
        rmin
        rmax
        nr
        zmin
        zmax
        nz
        freq: frequency in MHz
        data: 2D array of shape (nr, nz)    
    
    
    """
    
    # Read header
    # xmin(cm), xmax(cm), nx-1
    # freq(MHz)
    # ymin(cm), ymax(cm), ny-1
    with open(t7file, 'r') as f:
        line1 = f.readline().split()
        freq_MHz = float(f.readline())
        line3 = f.readline().split()
    
    # Form output dict 
    d = {}
    d['zmin'], d['zmax'], d['nz'] =  float(line1[0]), float(line1[1]), int(line1[2])+1
    d['freq'] = freq_MHz
    d['rmin'], d['rmax'], d['nr'] =  float(line3[0]), float(line3[1]), int(line3[2])+1
    
    # These should be the labels
    labels=['Ez', 'Er', 'E', 'Hphi']
    
    # Read and reshape
    dat4 = np.loadtxt(t7file, skiprows=3)
    ncol = len(labels)
    dat4 = dat4.reshape(d['nr'], d['nz'], ncol)
    
    
    for i, label in enumerate(labels):
        d[label] = dat4[:,:,i]
    
    
    return d

def parse_poisson_t7(t7file, type='electric', geometry='cylindrical'):
    """
    Parses a T7 file. The T7 header should have:
    
    xmin(cm), xmax(cm), nx-1
    ymin(cm), ymax(cm), ny-1
    
    For type=='electric':
        2 columns of data: Ez, Er
        Units are in V/cm
    
    For type=='magnetic':
        2 columns of data: Bz, Br
        Units are G
    
    Returns a dict with:
        rmin
        rmax
        nr
        ymin
        ymax
        ny
        data: 2D array of shape (nx, ny)    
    
    
    """
    assert geometry == 'cylindrical', 'TODO: other geometries'

    if type == 'electric':
        labels = 'Er', 'Ez'
    elif type == 'magnetic':
        labels = 'Br', 'Bz'
        
    # Read header
    # xmin(cm), xmax(cm), nx-1    # r in cylindrical geometry
    # ymin(cm), ymax(cm), ny-1    # z in cylindrical geometry
    with open(t7file, 'r') as f:
        xline = f.readline().split()
        yline = f.readline().split()

    # Form output dict 
    d = {}
    d['rmin'], d['rmax'], d['nr'] =  float(xline[0]), float(xline[1]), int(xline[2])+1
    d['zmin'], d['zmax'], d['nz'] =  float(yline[0]), float(yline[1]), int(yline[2])+1
    
    # Read and reshape
    dat4 = np.loadtxt(t7file, skiprows=2)
    ncol = len(labels)
    dat4 = dat4.reshape(d['nz'], d['nr'], ncol)
    
    for i, label in enumerate(labels):
        d[label] = dat4[:,:,i].T
    
    
    return d



#_________________________________
#_________________________________
# Individual parsers



#_________________________________
# Header

def parse_header_variable(line):
    """
    Parses a line that follows:
    
    Variable Code         Value     Description
    
    Returns:
        key, value, description, in_automesh
    
    """
    x = line.split()
    
    key = x[0]
    
    if x[1] == 'A':
        in_automesh = True
        
        s = x[2]
        d = x[3:]
    else:
        in_automesh = False
        s = x[1]
        d = x[2:]
        
    descrip = ' '.join(d)
        
    try: 
        val = int(s)
    except ValueError:
        val = float(s)
    
    return key, val, descrip, in_automesh


def parse_header_lines(lines):
    """
    Parses the header lines
    """
    
    
    header = 'Variable Code         Value     Description'
    
    d = {}
    description = {}
    in_automesh = {}
    
    comments = []
    
    in_header=False
    for line in lines:
        if line == header:
            in_header = True
            continue
        if not in_header:
            comments.append(line)
            continue
        
        key, val, descrip, in_am = parse_header_variable(line)
        
        d[key] = val
        description[key] = descrip
        in_automesh[key] = in_am
        
    return {'variable':d, 'description':description, 'in_automesh':in_automesh, 'comments':'\n'.join(comments)}


#_________________________________
# Wall segments




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
    
    inside = False
    fields = None
    units = None

    for L in lines[1:]:

        L = L.strip()

        # Look for key=value
        if '=' in L:
            key, val = L.split('=')
            info[key.strip()] = val
            continue

        if L.startswith("K    L"):                
            nskip = 2
            fields = {name.strip('|'):[] for name in L.split()[nskip:]}
            continue
        elif L.startswith( "m     K     L"):
            nskip = 3
            fields = {name.strip('|'):[] for name in L.split()[nskip:]}            
            continue

        if not fields:
            continue        
    
        # Look for units
        if fields and not units:
            unit_labels = L.split()
            assert len(unit_labels) == len(fields), print(unit_labels)
            # make dict
            units = dict(zip(list(fields),unit_labels))
            inside = True
            continue

        # This might come at the end
        if L.startswith('Summary'):
            inside = False
            
            
        # Must be inside. Add data            
        if inside:
            x = [float(y) for y in L.split()]
            # Special care if there are blanks for the skip columns 
            if len(x) == len(fields) + nskip:
                x =  x[nskip:]
            for i, name in enumerate(fields):
                fields[name].append(x[i])

    # Exiting
    for k, v in fields.items():
        fields[k] = np.array(v)            
    
    return {'wall':fields, 'info':info, 'units':units}




#_________________________________
# Summary

def parse_sfo_beam_energy(lines):
    d_vals = {}
    d_units = {}
    for line in lines:
        line = line.strip()
        if line.startswith('V0'):
            line = line.split('=')[-1]
            line = line.strip()
            line = line.split(' ')
            data = line[0]
            data = float(data)
            unit = line[1]
    d_vals['BeamEnergy'] = data
    d_units['BeamEnergy'] = unit
    return d_vals, d_units


def parse_sfo_summary_group(lines):
    """
    """
    d_vals = {}
    d_units = {}
    for line in lines:
        if line == "":
            break
        else:
            d_val, d_unit = parse_sfo_summary_group_line(line)
            d_vals.update(d_val)
            d_units.update(d_unit)
    return d_vals, d_units

def parse_simple_summary_line(line):
    # deal with simple line with one key and one value
    d_val = {}
    d_unit = {}
    line = line.split("=")
    if len(line) == 1:
        return d_val, d_unit
    key = line[0].strip()
    val = line[-1]
    val = val.strip()
    val = val.split(" ")
    d_val[key] = float(val[0])
    if len(val) > 1:
        d_unit[key] = val[1]
    else:
        d_unit[key] = ""
    return d_val, d_unit

def parse_sfo_summary_group_line(line):
    d_val = {}
    d_unit = {}
    if line.startswith('Field normalization'):
        line = line.split("=")
        val = line[-1]
        val = val.strip()
        val = val.split(" ")
        d_val['Enorm'] = float(val[0])
        d_unit['Enorm'] = val[1]
        return d_val, d_unit
# 'for the integration path from point Z1,R1 =     50.50000 cm,   0.00000 cm',
    if line.startswith('for the integration path'):
        line = line.split("=")
        val = line[-1]
        val = val.strip()
        val = val.split(",")
        v1 = val[0].split(" ")
        v1 = v1[0]
        v2 = val[1].strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val['integration_Z1'] = float(v1)
        d_unit['integration_Z1'] = "cm"
        d_val['integration_R1'] = float(v2)
        d_unit['integration_R1'] = "cm"
        return d_val, d_unit
#  'to ending point                     Z2,R2 =     50.51000 cm,   0.00000 cm',
    if line.startswith('to ending point'):
        line = line.split("=")
        val = line[-1]
        val = val.strip()
        val = val.split(",")
        v1 = val[0].split(" ")
        v1 = v1[0]
        v2 = val[1].strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val['integration_Z2'] = float(v1)
        d_unit['integration_Z2'] = "cm"
        d_val['integration_R2'] = float(v2)
        d_unit['integration_R2'] = "cm"
        return d_val, d_unit
    if line.startswith('Beta '):
        # custom parse the beta line
        line = line.split("=")
        beta = line[1].strip()
        beta = beta.split(" ")
        beta = beta[0]
        ke = line[-1]
        ke = ke.strip()
        ke = ke.split(" ")
        ke = ke[0]
        d_val['beta'] = float(beta)
        d_val['kinetic_energy'] = float(ke)
        d_unit['beta'] = ""
        d_unit['kinetic_energy'] = "MeV"
        return d_val, d_unit
#   'Q    =  0.334933E+10      Shunt impedance =  2001715.397 MOhm/m',
    if line.startswith('Q '):
        # Q factor line
        line = line.split("=")
        v1 = line[1].strip()
        v1 = v1.split(" ")
        v1 = v1[0]
        v2 = line[-1]
        v2 = v2.strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val['Q'] = float(v1)
        d_val['Shunt impedance'] = float(v2)
        d_unit['Q'] = ""
        d_unit['Shunt impedance'] = "MOhm/m"
        return d_val, d_unit
#          'Rs*Q =    81.364 Ohm                Z*T*T =  1956056.397 MOhm/m',
    if line.startswith('Rs*Q '):
        # Q factor line
        line = line.split("=")
        v1 = line[1].strip()
        v1 = v1.split(" ")
        v1 = v1[0]
        v2 = line[-1]
        v2 = v2.strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val['Rs*Q'] = float(v1)
        d_val['Z*T*T'] = float(v2)
        d_unit['Rs*Q'] = "Ohm"
        d_unit['Z*T*T'] = "MOhm/m"
        return d_val, d_unit
# 'r/Q  =   134.323 Ohm  Wake loss parameter =      0.04044 V/pC',
    if line.startswith('r/Q '):
        # r/Q line
        line = line.split("=")
        v1 = line[1].strip()
        v1 = v1.split(" ")
        v1 = v1[0]
        v2 = line[-1]
        v2 = v2.strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val['r/Q'] = float(v1)
        d_val['Wake loss parameter'] = float(v2)
        d_unit['r/Q'] = "Ohm"
        d_unit['Wake loss parameter'] = "V/pC"
        return d_val, d_unit
#  'Average magnetic field on the outer wall  =      16678.8 A/m, 0.337887 mW/cm^2',
    if line.startswith('Average magnetic '):
        # Average magnetic field line
        line = line.split("=")
        val = line[-1]
        val = val.strip()
        val = val.split(",")
        v1 = val[0].split(" ")
        v1 = v1[0]
        d_val['AvgH'] = float(v1)
        d_unit['AvgH'] = "A/m"
        return d_val, d_unit
#  'Maximum H (at Z,R = 25.1487,18.4727)      =       41189. A/m, 2.06066 mW/cm^2',
    if line.startswith('Maximum H '):
        # Maximum H line
        line = line.split("=")
        val = line[1].strip()
        val = val.split(",")
        v1 = val[0]
        v2 = val[1].split(")")
        v2 = v2[0]
        v3 = line[-1]
        v3 = v3.strip()
        v3 = v3.split(",")
        v3 = v3[0].split(" ")
        v3 = v3[0]
        d_val['MaxH_z'] = float(v1)
        d_val['MaxH_r'] = float(v2)
        d_val['MaxH'] = float(v3)
        d_unit['MaxH_z'] = 'cm'
        d_unit['MaxH_r'] = 'cm'
        d_unit['MaxH'] = "A/m"
        return d_val, d_unit
#  'Maximum E (at Z,R = 49.9969,0.624269)     =      41.1564 MV/m, 2.84161 Kilp.',
    if line.startswith('Maximum E '):
        # Maximum E line
        line = line.split("=")
        val = line[1].strip()
        val = val.split(",")
        v1 = val[0]
        v2 = val[1].split(")")
        v2 = v2[0]
        v3 = line[-1]
        v3 = v3.strip()
        v3 = v3.split(",")
        v3 = v3[0].split(" ")
        v3 = v3[0]
        d_val['MaxE_z'] = float(v1)
        d_val['MaxE_r'] = float(v2)
        d_val['MaxE'] = float(v3)
        d_unit['MaxE_z'] = 'cm'
        d_unit['MaxE_r'] = 'cm'
        d_unit['MaxE'] = "MV/m"
        return d_val, d_unit
    else:
        d_val, d_unit = parse_simple_summary_line(line)
    return d_val, d_unit
