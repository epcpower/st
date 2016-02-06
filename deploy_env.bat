set SYSROOT=C:\epc\t\134\pqd\sysroot
REM set QMAKE=C:\Qt\Qt5.5.1\5.5\msvc2010\bin\qmake.exe
REM SET PATH=%_ROOT%\qtbase\bin;%_ROOT%\gnuwin32\bin;%PATH%
set INTERPRETER=C:/Python34/python.exe
set CL=/MP

REM http://doc.qt.io/qt-5/windows-building.html#step-3-set-the-environment-variables
REM Set up \Microsoft Visual Studio 2013, where <arch> is \c amd64, \c x86, etc.
REM CALL "C:\Program Files (x86)\Microsoft Visual Studio 12.0\VC\vcvarsall.bat" <arch>
SET _ROOT=C:\qt\Qt5.5.1
SET PATH=%_ROOT%\qtbase\bin;%_ROOT%\gnuwin32\bin;%PATH%
SET PATH=%_ROOT%\5.5\msvc2010\bin;%PATH%
REM Uncomment the below line when using a git checkout of the source repository
REM SET PATH=%_ROOT%\qtrepotools\bin;%PATH%
SET QMAKESPEC=win32-msvc2010
SET _ROOT=

call "C:\Program Files (x86)\Microsoft Visual Studio 10.0\VC\vcvarsall.bat" x86

REM SIP
REM pyqtdeploycli --package sip --target win-32 configure
REM python configure.py --static --sysroot=%SYSROOT% --no-tools --use-qmake --configuration=sip-win.cf
REM qmake
REM nmake
REM nmake install

REM pyqt5
REM pyqtdeploycli --package pyqt5 --target win-32 configure
REM
REM    # must be available in C:\Qt\Qt5.5.1\5.5\msvc2010\lib
REM    target_config.pyqt_modules.remove('QAxContainer')
REM    target_config.pyqt_modules.remove('QtLocation')
REM    target_config.pyqt_modules.remove('QtPositioning')
REM    target_config.pyqt_modules.remove('QtOpenGL')
REM    target_config.pyqt_modules.remove('_QOpenGLFunctions_ES2')
REM    # Check which modules to build if we haven't been told.
REM    if len(target_config.pyqt_modules) == 0:
REM        check_modules(target_config, opts.disabled_modules, opts.verbose)
REM
REM python configure.py --static --sysroot=%SYSROOT% --no-tools --no-qsci-api --no-designer-plugin --no-qml-plugin --configuration=pyqt5-win.cfg
REM nmake
REM nmake install

REM pyqtdeploy
REM doesn't work because of mercurial issues.  nmake pyqtdeploy/version.py
REM 
