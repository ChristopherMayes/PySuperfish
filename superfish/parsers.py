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

        d.update(parse_sfo_segment([line1]+lines))


    else:
        # No parser yet:
        if verbose:
            print('No parser for:', rtype)

        d['type'] = rtype
        d['lines'] = lines

    return d


#_________________________________
#_________________________________
# Individual parsers



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

    assert len(dats)==1, 'multiple blocks found'

    return {'wall':dats[0], 'info':info}




#_________________________________
# Summary




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
