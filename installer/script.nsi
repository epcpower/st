!include "MUI2.nsh"

# define installer name
!define /file VERSION "..\version.txt"
OutFile "..\dist\epyq-${VERSION}.exe"

!define MUI_ICON "..\epyq\icon.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "..\epyq\icon.png"
!define MUI_HEADERIMAGE_RIGHT

# set desktop as install directory
InstallDir $PROFILE\epyq

PageEx directory
  DirVar $INSTDIR
PageExEnd

Page instfiles

# default section start
Section

# define output path
SetOutPath $INSTDIR

# specify file to go in output path
File /r "..\dist\epyq\"

# define uninstaller name
WriteUninstaller $INSTDIR\uninstaller.exe


#-------
# default section end
SectionEnd

# create a section to define what the uninstaller does.
# the section will always be named "Uninstall"
Section "Uninstall"

# Always delete uninstaller first
Delete $INSTDIR\uninstaller.exe

# now delete installed file
RMDir /r $INSTDIR

SectionEnd