from . import parsers
from .plot import plot_wall
from .interpolate import interpolate2d

import os
import platform
import subprocess
import tempfile
from time import time
import shutil


class Superfish:
    
    # Class attributes for the container
    _container_image = 'hhslepicka/poisson-superfish:latest'
    _windows_exe_path = 'C:\\LANL\\'  # Windows only'
    _singularity_image = '~/poisson-superfish_latest.sif'

    # Automatically detect the container method
    if shutil.which('docker'):
        _container_command = 'docker run {interactive_flags} --rm -v {local_path}:/data/ {image} {cmds}'
    elif shutil.which('shifter'):
        _container_command = 'shifter --image={image} {cmds}'
    elif shutil.which('singularity'):
        _container_command = 'singularity exec --bind {local_path}:/data/ {singularity_image} {cmds}'
    else:
        _container_command = None

    def __init__(
            self,
            automesh=None,
            problem='fish',
            use_tempdir=True,
            use_container='auto',
            interactive=False,
            workdir=None,
            verbose=True):
        """
        Poisson-Superfish object
        
        
        """
        self.configured = False
        self.problem = problem
            
        self.verbose = verbose
        self.use_tempdir = use_tempdir
        self.interactive = interactive
        if workdir:
            workdir = os.path.abspath(workdir)
            assert os.path.exists(workdir), f'workdir does not exist: {workdir}'           
        self.workdir = workdir
            
        if automesh:
            self.load_input(automesh)
            self.configure()

        if use_container == 'auto':
            if platform.system() == 'Windows' and os.path.exists(self._windows_exe_path):
                self.use_container = False
                self.vprint(f'Using executables installed in {self._windows_exe_path}')
                
            else:
                self.vprint(f'Using container on {platform.system()}:')
                self.vprint('    ', self._container_command)
                self.use_container = True
            
        else:
            self.use_container = use_container

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

    def interpolate(self, zmin=-1000, zmax=1000, nz=100, rmin=0, rmax=0, nr=1):
        """
        Interpolates field over a grid. 
        """
    
        t7data = interpolate2d(
            self,
            zmin=zmin, zmax=zmax, nz=nz,
            rmin=rmin, rmax=rmax, nr=nr
        )
        
        return t7data

    def run(self):
        """
        Writes input, runs autofish, and loads output
        
        """
        
        assert self.configured, 'not configured to run'
        
        self.write_input()
        
        t0 = time()
        
        if self.problem == 'fish':
            self.run_cmd('autofish', self.automesh_name)    
        else:
            self.run_cmd('automesh', self.automesh_name) 
            self.run_cmd('poisson')    
            self.run_cmd('sfo')    
           
        dt = time() - t0
        self.vprint(f'Done in {dt:10.2f} seconds')
        
        self.load_output()
        
    def container_run_cmd(self, *args):
        """
        Returns the run command string for the container.
        
        The container data should live in its /data/ folder.
        
        """
        
        cmds = ' '.join(args)

        if self.interactive:
            assert platform.system() == 'Darwin', 'TODO interactive non-Darwin'
            cmd0 = "IP=$(ifconfig en0 | grep inet | awk '$1==\"inet\" {print $2}');xhost + $IP;"
            interactive_flags = "-e INTERACTIVE_FISH=1 -e DISPLAY=$IP:0"
        else:
            cmd0 = ''
            interactive_flags = ''

        cmd = self._container_command.format(
            local_path=self.path,
            image=self._container_image,
            interactive_flags=interactive_flags,
            cmds=cmds,
            singularity_image=self._singularity_image
        )
        
        return cmd0+cmd
    
    def windows_run_cmd(self, *args):
        
        cmd = os.path.join(self._windows_exe_path, args[0].upper()+'.EXE')
        
        assert os.path.exists(cmd), f'EXE does not exist: {cmd}'
        
        if len(args) > 1:
            cmd = cmd + ' ' + ' '.join(args[1:])
       
        return cmd
        
    def run_cmd(self, *cmds, **kwargs):
        """
        Runs a command in in self.
        
        Example:
            .run_cmd(['C:\LANL\AUTOMESH.EXE', 'TEST.AM'], timeout=1)
        
        """
        if platform.system() == 'Windows':
            cmds = self.windows_run_cmd(*cmds)
        else:
            cmds = self.container_run_cmd(*cmds)
        
        self.vprint(f'Running: {cmds}')
    
        logfile = os.path.join(self.path, 'output.log')
    
        if self.use_container:
            
            # Shifter doesn't need volume mounting
            if self._container_command.startswith('shifter'):
                cwd=self.path
            else:
                cwd=None
           
            with open(logfile, "a") as output:
                P = subprocess.call(
                    cmds, shell=True, stdout=output, stderr=output, cwd=cwd,
                    **kwargs
                )
        else:
            # Windows needs this
            P = subprocess.run(cmds.split(), cwd=self.path, **kwargs)
            
        return P
    
        ## Actual run
        #P = subprocess.run(cmds, shell=True, cwd=self.path, **kwargs)
        #
        #print(P)
        #
        #return P
    
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
        
        if not os.path.exists(sfofile):
            self.vprint('Warking: no SFO file to load.')
            return
        
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

    def __repr__(self):
        memloc = hex(id(self))
        if self.configured:
            return f'<Superfish configured to run in {self.path}>' 
        
        return f'<Superfish at {memloc}>'        
