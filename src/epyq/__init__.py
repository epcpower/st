from src.epyq import __version__, __sha__, __revision__

__version_tag__ = 'v{}-{}'.format(__version__, __sha__)
__build_tag__ = src.epyq._build.job_id
