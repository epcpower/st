# For development and git commit, the __version__ is set to the build placeholder 0.0.0
# For release, the __version__ is modified by poetry dynamic versioning with the actual released version
__version__ = "0.0.0"

import epyq._build

__version_tag__ = "v{}".format(__version__)
__build_tag__ = epyq._build.job_id


# from epyq._version import __version__, __sha__, __revision__
# import epyq._build
#
# __version_tag__ = "v{}-{}".format(__version__, __sha__)
# __build_tag__ = epyq._build.job_id
