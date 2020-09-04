from epyq._version import __version__, __sha__, __revision__
import epyq._build

__version_tag__ = "v{}-{}".format(__version__, __sha__)
__build_tag__ = epyq._build.job_id
