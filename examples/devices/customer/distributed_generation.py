__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def referenced_files(raw_dict):
    return ()


class DeviceExtension:
    def __init__(self, device):
        self.device = device()

        self.dash = None
        self.combo = None
        self.command = None
        self.measured = None
        self.power_command_frames = ()
        self.current_command_frames = ()
        self.pump_reset_controller_signal = None
        self.dc_control_command_frames = () # Added new object for dc control.

    def post(self):
        self.dash = self.device.ui.tabs.widget(0)
        self.setup = self.device.ui.tabs.widget(1)

        self.combo = self.dash.power_current_combo
        self.command = self.dash.stacked_command
        self.measured = self.dash.stacked_measured

        self.power_command_frames = {
            widget.ui.command.signal_object.frame
            for widget in
            (self.dash.real_power_command, self.dash.reactive_power_command)
        }

        self.current_command_frames = {
            widget.ui.command.signal_object.frame
            for widget in
            (self.dash.real_current_command, self.dash.reactive_current_command)
        }

        # This updates the new dc_control_command_frames object.
        self.dc_control_command_frames = {
            widget.ui.command.signal_object.frame
            for widget in
            (self.dash.dc_current_limit_command, self.dash.dc_voltage_limit_command)
        }

        self.combo.currentTextChanged.connect(self.combo_changed)

        self.combo.addItem('Power')
        self.combo.addItem('Current')
        self.combo.addItem('DC Control') # Added new option to the drop down menu.

        self.setup.pump_reset_button.value.pressed.connect(
            self.setup.pump_reset_controller_button.pressed
        )
        self.setup.pump_reset_button.value.released.connect(
            self.setup.pump_reset_controller_button.released
        )

    def combo_changed(self, text):
        if text == 'Power':
            self.command.setCurrentIndex(0)
            self.measured.setCurrentIndex(1)
        elif text == 'Current':
            self.command.setCurrentIndex(1)
            self.measured.setCurrentIndex(0)
        elif text == 'DC Control': 
            self.command.setCurrentIndex(2) # Added new else if statement.
            self.measured.setCurrentIndex(0)

        for frame in self.power_command_frames:
            frame.block_cyclic = text != 'Power'
        for frame in self.current_command_frames:
            frame.block_cyclic = text != 'Current'
        for frame in self.dc_control_command_frames: # Added new for loop for the 3rd option.
            frame.block_cyclic = text != 'DC Control'