# For development and git commit, the __version__ variable below is set
# to the build placeholder "0.0.0". (In other words: leave alone!)
# For release/distribution, the __version__ variable below is modified
# during CI by poetry dynamic versioning with the github tagged version.
__version__ = "0.0.0"

import epyq._build

__version_tag__ = "v{}".format(__version__)
__build_tag__ = epyq._build.job_id