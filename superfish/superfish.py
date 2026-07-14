import os
import platform
import shutil
import subprocess
import tempfile
from time import time
from typing import TYPE_CHECKING, Any

from . import parsers
from .interpolate import interpolate2d
from .plot import plot_wall

if TYPE_CHECKING:
    from beamphysics import FieldMesh


class Superfish:
    """
    Interface to the Poisson Superfish programs.

    Manages a working directory, runs the Poisson Superfish programs
    (natively on Windows, or through a container elsewhere), and parses
    their output.

    Attributes
    ----------
    input : dict
        Input data with ``basename`` and ``automesh`` (lines) keys.
    output : dict
        Parsed output, filled by :meth:`load_output`.
    path : str
        Working directory where the programs run.
    use_container : bool
        Whether commands run through a container.
    container_method : str or None
        Selected container orchestration method.
    """

    # Class attributes for the container. The image tag and Singularity .sif
    # path can be overridden via the PYSUPERFISH_CONTAINER_IMAGE /
    # PYSUPERFISH_SINGULARITY_IMAGE environment variables, which build.sh
    # honors as well so one variable configures both build and runtime.
    _container_image = os.environ.get(
        "PYSUPERFISH_CONTAINER_IMAGE", "poisson-superfish:latest"
    )
    _windows_exe_path = "C:\\LANL\\"  # Windows only'
    _singularity_image = os.environ.get(
        "PYSUPERFISH_SINGULARITY_IMAGE", "~/poisson-superfish_latest.sif"
    )
    # Default container method; None means auto-detect
    _container_method = os.environ.get("PYSUPERFISH_CONTAINER_METHOD")

    _container_commands = {
        "docker": (
            "docker run {interactive_flags} --rm -v {local_path}:/data/ {image} {cmds}"
        ),
        "shifter": "shifter --image={image} {cmds}",
        "singularity": "singularity exec {singularity_image} {cmds}",
    }

    @classmethod
    def _detect_container_method(cls) -> str | None:
        """
        Pick a container method based on the available executables.

        Prefers Singularity when its image file already exists, then Docker,
        then Shifter, then Singularity even without a pre-built image.

        Returns
        -------
        str or None
            The detected method name, or None if no method is available.
        """
        if shutil.which("singularity") and os.path.exists(
            os.path.expanduser(cls._singularity_image)
        ):
            return "singularity"
        if shutil.which("docker"):
            return "docker"
        if shutil.which("shifter"):
            return "shifter"
        if shutil.which("singularity"):
            return "singularity"
        return None

    @property
    def container_command(self) -> str | None:
        """Command template for the selected container method, or None."""
        if self.container_method is None:
            return None
        return self._container_commands[self.container_method]

    def __init__(
        self,
        automesh: str | None = None,
        problem: str = "fish",
        use_tempdir: bool = True,
        use_container: str | bool = "auto",
        container_method: str | None = None,
        interactive: bool = False,
        workdir: str | None = None,
        verbose: bool = True,
    ) -> None:
        """
        Poisson-Superfish object

        Parameters
        ----------
        automesh : str, optional
            Path to an automesh input file. If given, it is loaded and the
            object is configured to run.
        problem : {"fish", "poisson"}
            Type of problem to run.
        use_tempdir : bool
            Run in a temporary directory instead of in place.
        use_container : "auto" or bool
            Whether to run through a container. "auto" uses the native
            executables on Windows and a container elsewhere.
        container_method : {"docker", "shifter", "singularity"}, optional
            Container orchestration method. If not given, defaults to the
            PYSUPERFISH_CONTAINER_METHOD environment variable; if that is
            also unset, the first available method is auto-detected:
            Singularity with an existing image, then Docker, then Shifter,
            then Singularity without an image.
        interactive : bool
            Run the container in interactive (X11) mode. macOS only.
        workdir : str, optional
            Base directory for the working directory.
        verbose : bool
            Print progress messages.
        """
        self.configured = False
        self.problem = problem

        self.verbose = verbose
        self.use_tempdir = use_tempdir
        self.interactive = interactive
        if workdir:
            workdir = os.path.abspath(workdir)
            assert os.path.exists(workdir), f"workdir does not exist: {workdir}"
        self.workdir = workdir

        if automesh:
            self.load_input(automesh)
            self.configure()

        if container_method is None:
            container_method = self._container_method
        if container_method is None:
            container_method = self._detect_container_method()
        else:
            container_method = str(container_method).lower()
            if container_method not in self._container_commands:
                options = ", ".join(sorted(self._container_commands))
                raise ValueError(
                    f"Unknown container_method {container_method!r}; "
                    f"choose from: {options}"
                )
        self.container_method = container_method

        if use_container == "auto":
            if platform.system() == "Windows" and os.path.exists(
                self._windows_exe_path
            ):
                self.use_container = False
                self.vprint(f"Using executables installed in {self._windows_exe_path}")

            else:
                self.vprint(
                    f"Using {self.container_method} container on {platform.system()}:"
                )
                self.vprint("    ", self.container_command)
                self.use_container = True

        else:
            self.use_container = use_container

    @property
    def basename(self) -> str:
        """Base name of the problem, from the automesh file name."""
        return self.input["basename"]

    @property
    def automesh_name(self) -> str:
        """Name of the automesh input file, ``<basename>.AM``."""
        return self.basename + ".AM"

    def param(self, key: str) -> int | float:
        """
        Look up a parameter from the readback in the SFO file.

        Parameters
        ----------
        key : str
            Variable or Constant name, e.g. ``"CONV"``.

        Returns
        -------
        int or float
            The parameter value.
        """
        return self.output["sfo"]["header"]["variable"][key]

    def param_info(self, key: str) -> str:
        """
        Look up the description of a parameter.

        Parameters
        ----------
        key : str
            Variable or Constant name, e.g. ``"CONV"``.

        Returns
        -------
        str
            The parameter description.
        """
        return self.output["sfo"]["header"]["description"][key]

    def configure(self) -> None:
        """
        Configure the working directory to run in.

        Creates a temporary directory when ``use_tempdir`` is set;
        otherwise runs in ``workdir`` or in place.
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

        self.vprint("Configured to run in:", self.path)

        self.configured = True

    def fieldmesh(
        self,
        zmin: float = -100,
        zmax: float = 100,
        nz: int = 0,
        dz: float = 0,
        rmin: float = 0,
        rmax: float = 100,
        nr: int = 0,
        dr: float = 0,
    ) -> "FieldMesh":
        """
        Interpolate the field over a grid, returning a FieldMesh.

        Similar to :meth:`interpolate`, but input units are in meters.

        Various combinations of the spacings and grid point numbers
        ``nz``, ``dz``, ``nr``, ``dr`` can be used. If neither is
        specified, a default of 100 grid points will be used.

        Parameters
        ----------
        zmin, zmax : float
            z extent of the grid, in meters.
        nz : int
            Number of z points.
        dz : float
            z spacing, in meters. Overrides ``zmax`` when given with
            ``nz``.
        rmin, rmax : float
            Radial extent of the grid, in meters.
        nr : int
            Number of radius points.
        dr : float
            Radial spacing, in meters. Overrides ``rmax`` when given with
            ``nr``.

        Returns
        -------
        FieldMesh
            An openPMD-beamphysics FieldMesh object.
        """

        conv = self.param("CONV")
        fac = 100 / conv

        # Various input possibilities for the grid
        if dz and nz:
            zmax = zmin + (nz - 1) * dz
        elif dz and not nz:
            nz = int((zmax - zmin) / dz) + 1
            zmax = zmin + (nz - 1) * dz
        elif not dz and not nz:
            # Default
            nz = 100

        if dr and nr:
            rmax = rmin + (nr - 1) * dr
        elif dr and not nr:
            nr = int((rmax - rmin) / dr) + 1
            rmax = rmin + (nr - 1) * dr
        elif not dr and not nr:
            # Default
            nr = 100

        FM = interpolate2d(
            self,
            zmin=zmin * fac,
            zmax=zmax * fac,
            nz=nz,
            rmin=rmin * fac,
            rmax=rmax * fac,
            nr=nr,
            return_fieldmesh=True,
        )

        return FM

    def interpolate(
        self,
        zmin: float = -1000,
        zmax: float = 1000,
        nz: int = 100,
        rmin: float = 0,
        rmax: float = 0,
        nr: int = 1,
    ) -> dict[str, Any]:
        """
        Interpolate the field over a grid.

        Parameters
        ----------
        zmin, zmax : float
            z extent of the grid, in the problem's input units.
        nz : int
            Number of z points.
        rmin, rmax : float
            Radial extent of the grid, in the problem's input units.
        nr : int
            Number of radius points.

        Returns
        -------
        dict
            t7data dict, as returned by
            :func:`superfish.interpolate.interpolate2d`.
        """

        t7data = interpolate2d(
            self, zmin=zmin, zmax=zmax, nz=nz, rmin=rmin, rmax=rmax, nr=nr
        )

        return t7data

    def run(self) -> None:
        """
        Write input, run the problem, and load the output.

        Runs ``autofish`` for fish problems, or the
        ``automesh``/``poisson``/``sfo`` chain for poisson problems.
        """

        assert self.configured, "not configured to run"

        self.write_input()

        t0 = time()

        if self.problem == "fish":
            self.run_cmd("autofish", self.automesh_name)
        else:
            self.run_cmd("automesh", self.automesh_name)
            self.run_cmd("poisson")
            self.run_cmd("sfo")

        dt = time() - t0
        self.vprint(f"Done in {dt:10.2f} seconds")

        self.load_output()

    def container_run_cmd(self, *args: str) -> str:
        """
        Form the run command string for the container.

        The container data should live in its /data/ folder.

        Parameters
        ----------
        *args : str
            Program name and arguments, e.g. ``("automesh", "TEST.AM")``.

        Returns
        -------
        str
            The full shell command.

        Raises
        ------
        RuntimeError
            If no container method is available.
        """

        cmds = " ".join(args)

        template = self.container_command
        if template is None:
            raise RuntimeError(
                "No container method available: "
                "docker, shifter, or singularity not found"
            )

        if self.interactive:
            assert platform.system() == "Darwin", "TODO interactive non-Darwin"
            cmd0 = "IP=$(ifconfig en0 | grep inet | awk '$1==\"inet\" {print $2}');xhost + $IP;"
            interactive_flags = "-e INTERACTIVE_FISH=1 -e DISPLAY=$IP:0"
        else:
            cmd0 = ""
            interactive_flags = ""

        cmd = template.format(
            local_path=self.path,
            image=self._container_image,
            interactive_flags=interactive_flags,
            cmds=cmds,
            singularity_image=self._singularity_image,
        )

        return cmd0 + cmd

    def windows_run_cmd(self, *args: str) -> str:
        """
        Form the run command string for the native Windows executables.

        Parameters
        ----------
        *args : str
            Program name and arguments, e.g. ``("automesh", "TEST.AM")``.

        Returns
        -------
        str
            The full command.
        """
        cmd = os.path.join(self._windows_exe_path, args[0].upper() + ".EXE")

        assert os.path.exists(cmd), f"EXE does not exist: {cmd}"

        if len(args) > 1:
            cmd = cmd + " " + " ".join(args[1:])

        cmd = f"wine {cmd}"

        return cmd

    def run_cmd(self, *cmds: str, **kwargs: Any) -> int | subprocess.CompletedProcess:
        r"""
        Run a Superfish program in the working directory.

        Output is appended to ``output.log`` in the working directory when
        running through a container.

        Parameters
        ----------
        *cmds : str
            Program name and arguments, e.g. ``("automesh", "TEST.AM")``.
        **kwargs
            Passed to ``subprocess.call`` (container) or
            ``subprocess.run`` (native Windows).

        Returns
        -------
        int or subprocess.CompletedProcess
            The return code (container), or the completed process (native
            Windows).

        Examples
        --------
        >>> sf.run_cmd("automesh", "TEST.AM", timeout=1)
        """
        if self.use_container:
            cmds = self.container_run_cmd(*cmds)
        else:
            cmds = self.windows_run_cmd(*cmds)

        self.vprint(f"Running: {cmds}")

        logfile = os.path.join(self.path, "output.log")

        if self.use_container:
            # Shifter and Singularity don't need volume mounting
            if self.container_method in ("shifter", "singularity"):
                cwd = self.path
            else:
                cwd = None

            with open(logfile, "a") as output:
                P = subprocess.call(
                    cmds, shell=True, stdout=output, stderr=output, cwd=cwd, **kwargs
                )
        else:
            # Windows needs this
            P = subprocess.run(cmds.split(), cwd=self.path, **kwargs)

        return P

    def load_input(self, input_filePath: str) -> None:
        """
        Load an automesh input file.

        Parameters
        ----------
        input_filePath : str
            Path to the automesh (.AM) file.
        """
        f = os.path.abspath(input_filePath)

        # Get basename. Should be upper case to be consistent with output files (that are always upper case)
        _, fname = os.path.split(f)
        basename = os.path.splitext(fname)[0].upper()
        self.input = dict(basename=basename)

        self.input["automesh"] = parsers.parse_automesh(f)

    def load_output(self) -> None:
        """
        Load and parse the SFO output file into ``.output["sfo"]``.
        """

        self.output = {}

        sfofile = os.path.join(self.path, self.basename + ".SFO")

        if not os.path.exists(sfofile):
            self.vprint("Warking: no SFO file to load.")
            return

        self.output["sfo"] = parsers.parse_sfo(sfofile)

        self.vprint("Parsed output:", sfofile)

    def plot_wall(self, units: str = "original", **kwargs: Any) -> None:
        """
        Plot the problem geometry from the parsed wall segments.

        Parameters
        ----------
        units : {"original", "cm"}
            Units for the plot axes. ``"cm"`` converts using the problem's
            CONV parameter.
        **kwargs
            Passed to :func:`superfish.plot.plot_wall`.
        """
        if units == "original":
            conv = 1
        elif units == "cm":
            conv = self.param("CONV")
        else:
            raise ValueError(f"Units must be original or cm: {units}")

        plot_wall(self.output["sfo"]["wall_segments"], conv=conv, **kwargs)

    def write_input(self) -> None:
        """
        Write the automesh input file from ``.input["automesh"]``.
        """

        file = os.path.join(self.path, self.input["basename"] + ".AM")
        with open(file, "w") as f:
            for line in self.input["automesh"]:
                f.write(line)

    def vprint(self, *args: Any) -> None:
        """Print only when verbose is enabled."""
        if self.verbose:
            print(*args)

    def __repr__(self) -> str:
        memloc = hex(id(self))
        if self.configured:
            return f"<Superfish configured to run in {self.path}>"

        return f"<Superfish at {memloc}>"
