# Changelog for st

All changes to the st project will be documented in this file.
For instructions, see the [changelog confluence page](https://epcpower.atlassian.net/l/c/zM7wz0at).

-------------------------------------------------------------------------------

## [Unreleased] - YYYY-MM-DD

## [v2022.10] - 2022-10-19

### Added

- SC-774: Add aliases for Software Hash, Data Logger Block Header, Data Logger Record Header
- SC-572: Added changelog for release notes.
- SC-310: Parameters tab Auto Read checked off by default

### Changed

- SC-278: Cleanup for documentation, minor style change in main

### CI

- SC-1099: Update ci.yml actions to fix poetry version issue
- SC-1099: Update actions versions to alleviate CI build warnings
- SC-798: Release v2022.10
- SC-760: Pin poetry to 1.1.15 & fix boto3 ref
- SC-398: Romp Removal / Poetry Implementation
- SC-216: Github Actions CI

### Fixed

- SC-769: Allow datalogger binary to load with empty SunSpec JSON
- SC-734: revert pyelftools to pre-poetry version

