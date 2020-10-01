import matplotlib.pyplot as plt
import matplotlib
from copy import copy

# Get a default color map
CMAP0 = copy(plt.get_cmap('plasma'))
CMAP0.set_under('white')

from mpl_toolkits.axes_grid1 import make_axes_locatable

import numpy as np


def add_t7data_to_axes(t7data, ax, field='E', cmap=None, vmin=1e-19, scale=1):
    """
    Adds a field from t7data to an axes ax. 
    
    scale will scale the extents, to account for different units.
    Example: scale=10 will place this data in cm on a plot in mm
    
    """

    
    extent = [t7data[k]*scale for k in ('zmin', 'zmax', 'rmin', 'rmax')]
    
    if not cmap:
        cmap = CMAP0
        
    if field in ('E', 'B') and field not in t7data:
        data = np.hypot(t7data[field+'r'], t7data[field+'z'])
    else:
        data = t7data[field]
        
    
    ax.imshow(np.flipud(data), extent=extent, cmap=cmap, vmin=vmin )
    
    return ax




def perp(x, y, scale=1):
    """
    Calculates perpendicular lines.
    
    Returns two np.array: PX, PY 
        where each has the shape: (len(x)-1, 2)
    
    To test:
    
        X = np.array([1,2,3,4,8])
        Y = np.array([4,5,6,9,10])
        
        fig, ax = plt.subplots()
        ax.set_aspect('equal')
        ax.plot(X, Y)
        for i in range(len(PX)):
           ax.plot(PX[i,:], PY[i,:])
        
    """
    dx = np.diff(x)
    dy = np.diff(y)
    norm = np.hypot(dx, dy)
    
    # perp
    px0 = x[:-1]+dx/2
    py0 = y[:-1]+dy/2
    px1 = px0 +dy/norm *scale
    py1 = py0 -dx/norm *scale
    
    return np.array([px0, px1]).T, np.array([py0, py1]).T

def add_wall_segment_to_axes(seg, ax, perp_scale=0, max_field=1, field='E', cmap=None, conv=1):
    """
    Adds wall segments to axes. 
    
    If perp_scal >0, the field strength will be drawn as a perpendicular line. 
    max_field and the color map are needed to color these
    
    
    """
    
    x = seg['wall']['Z']*conv
    y = seg['wall']['R']*conv

    # Wall segment
    ax.plot(x, y, color='black')
        
    if perp_scale:
        
        # Fetch the field
        F = seg['wall'][field]/max_field # field, E or B
    
        scales = perp_scale*F[:-1]
    
        px, py = perp(x, y, scale=scales)
        
        
        if not cmap:
            cmap = CMAP0    
        
        color = cmap(F[:-1])   

        # Draw perp lines
        for i in range(len(px)):
               ax.plot(px[i,:], py[i,:], color=color[i])
                
                
def plot_wall(wall_segments, 
              perp_scale=0, 
              field='E', 
              max_field=None,
              cmap=None,
              ax = None,
              **kwargs):
    """
    Plots the wall from wall segments.
    
    If perp_scale > 0, the field will be plotted
    
    conv is the unit conversion factor used by Superfish. 
    
    TODO: this is only for FISH problems so far
    
    """
    
    if not ax:
        fig, ax = plt.subplots( **kwargs)
    

    
    if not cmap:
        cmap = plt.get_cmap('plasma')    
    
    if perp_scale and not max_field:
        max_field = np.array([seg['wall'][field].max() for seg in wall_segments]).max()
    else:
        max_field = 0
    
    for seg in wall_segments:
        add_wall_segment_to_axes(seg, ax, perp_scale=perp_scale,
                                 field=field,
                                 max_field=max_field, cmap=cmap)
      
    # Labels and units
    units = wall_segments[0]['units']

    ax.set_aspect('equal')
    ax.set_xlabel('z '+units['Z'])
    ax.set_ylabel('r '+units['R'])    
    
    
    if perp_scale == 0:
        return
        
    divider = make_axes_locatable(ax)
    cax = divider.append_axes('right', size='5%', pad=0.05)
    
    # Legend units
    field_unit = units[field]
    
    # Tweak for convenience
    if field_unit=='(V/m)' and max_field >1e6:
        sc = 1e-6
        field_unit='(MV/m)'
    elif field_unit=='(V/cm)' and max_field >1e4:
        sc = 1e-4
        field_unit='(MV/m)'        
        
    else:
        sc = 1
     
    # Add legend
    norm = matplotlib.colors.Normalize(vmin=0, vmax=max_field*sc)
    fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
             cax=cax, orientation='vertical', label=f'|{field}| max {field_unit}')             
    
#plot_wall(SF.output['sfo']['wall_segments'], perp_scale=0, field='H', figsize=(20,8))                


