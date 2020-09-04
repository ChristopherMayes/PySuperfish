from . import parsers
from .plot import plot_wall

import os
import subprocess
import tempfile
from time import time





class Superfish:

    def __init__(self,
                automesh='test.am',
                use_tempdir=True,
                workdir=None,
                exe_path='C:\\LANL\\',
                verbose=True):
        """
        Poisson-Superfish object
        
        
        """
        
    
        self.load_input( automesh)
        
        if os.path.exists(exe_path):
            self.exe_path = exe_path
        else:
            self.exe_path = None
            self.vprint('Warning: exe_path does not exist:', exe_path)
        
        
        self.verbose=verbose       
        self.use_tempdir = use_tempdir
        
        if workdir:
            workdir = tools.full_path(workdir)
            assert os.path.exists(workdir), 'workdir does not exist: '+workdir   
        self.workdir = workdir  
        
        
    @property
    def basename(self):
        return self.input['basename']
    @property
    def automesh_name(self):
        return self.basename+'.AM'
    
        
    def configure(self):     
        """
        Configures paths to run in.
        """
        
        # Set paths
        if self.use_tempdir:

            # Need to attach this to the object. Otherwise it will go out of scope.
            self.tempdir = tempfile.TemporaryDirectory(dir=self.workdir)
            self.path = self.tempdir.name
            
        else:
            
            if self.workdir:
                self.path = self.workdir
                self.tempdir = None
            else:
                # Work in place
                self.path = self.original_path        
     
        self.vprint('Configured to run in:', self.path)
        
        self.configured = True  
        
        
        
    def run(self):
        
        assert self.configured, 'not configured to run'
        
        self.write_input()
        
        exe = os.path.join(self.exe_path, 'AUTOFISH.EXE') 
        
        assert os.path.exists(exe)
        
        cmd = [exe, self.automesh_name]
        
        t0 = time()
        
        self.vprint('Running', ' '.join(cmd), f'in {self.path}')

        self.run_cmd(cmd)
        
        dt = time() - t0
        self.vprint(f'Done in {dt:10.2f} seconds')
        
        
        self.load_output()
        
        
        
    def run_cmd(self, cmds, **kwargs):
        """
        Runs a command in in self.
        
        Example:
            .run_cmd(['C:\LANL\AUTOMESH.EXE', 'TEST.AM'], timeout=1)
        
        """
    
        P = subprocess.run(cmds, cwd=self.path, **kwargs)
        
        return P

    
    def load_input(self, input_filePath):
        """
        
        """
        f = os.path.abspath(input_filePath)
        
        # Get basename. Should be upper case to be consistent with output files (that are always upper case)
        _, fname = os.path.split(f) 
        basename = os.path.splitext(fname)[0].upper()
        self.input = dict(basename=basename)

        self.input['automesh'] = parsers.parse_automesh(f)  
        
        
    def load_output(self):
        """
        Loads SFO output file
        """
        
        self.output={}
        
        sfofile = os.path.join(self.path, self.basename+'.SFO')
        
        self.output['sfo'] = parsers.parse_sfo(sfofile)
        
        self.vprint('Parsed output:', sfofile)
        
        
    def plot_wall(self, **kwargs):
            plot_wall(self.output['sfo']['wall_segments'], **kwargs)
        
        
    
    def write_input(self):
        """
        Writes automesh input from .input['automesh']
        """
        
        file = os.path.join(self.path, self.input['basename']+'.AM')
        with open(file, 'w') as f:
            for line in self.input['automesh']:
                f.write(line)
        
        

    def vprint(self, *args):
        """verbose print"""
        if self.verbose:
            print(*args)        
            
