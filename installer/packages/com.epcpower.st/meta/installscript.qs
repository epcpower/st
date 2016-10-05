function Component()
{
    // default constructor
}

Component.prototype.createOperations = function()
{
    try {
        // call the base create operations function
        component.createOperations();
        if (systemInfo.productType == "windows") { 
            try {
                component.addOperation("CreateShortcut", "@TargetDir@/maintenancetool.exe", "@StartMenuDir@/Uninstall.lnk",
                    "workingDirectory=@TargetDir@", "iconPath=%SystemRoot%/system32/SHELL32.dll",
                    "iconId=2");
                component.addOperation("CreateShortcut", "@TargetDir@/source/designer.vbs", "@StartMenuDir@/EPyQ HMI - Designer.lnk",
                    "workingDirectory=@TargetDir@/source", "iconPath=@TargetDir@/epyq.exe",
                    "iconId=0");
                component.addOperation("CreateShortcut", "@TargetDir@/epyq.exe", "@StartMenuDir@/EPyQ_HMI.lnk",
                    "workingDirectory=@TargetDir@", "iconPath=@TargetDir@/epyq.exe",
                    "iconId=0");

                component.addOperation("CreateShortcut", "@TargetDir@/epyq.exe", "@DesktopDir@/EPyQ_HMI.lnk",
                    "workingDirectory=@TargetDir@", "iconPath=@TargetDir@/epyq.exe",
                    "iconId=1");
            } catch (e) {
                // Do nothing if key doesn't exist
            }
        }
    } catch (e) {
        print(e);
    }
}
