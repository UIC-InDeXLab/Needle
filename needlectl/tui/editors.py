from typing import Any, Dict, Callable

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import ScrollableContainer, Horizontal
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Button, Input, Static


class EditValueScreen(ModalScreen):
    """Modal screen for editing string values"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Submit"),
    ]

    def __init__(self, key: str, value: str):
        super().__init__()
        self.key = key
        self.current_value = value

    def compose(self) -> ComposeResult:
        with Static(id="dialog"):
            yield Static(f"Edit value for {self.key}", id="title")
            yield Input(value=self.current_value, id="value-input")
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        self.query_one("#value-input").focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save_value()
        else:
            self.app.pop_screen()

    def save_value(self) -> None:
        value = self.query_one("#value-input").value
        self.app.post_message(self.ValueChanged(self.key, value))
        self.app.pop_screen()

    class ValueChanged(Message):
        def __init__(self, key: str, value: str):
            self.key = key
            self.value = value
            super().__init__()


class ConfigEditorBase(App):
    """Base class for configuration editors"""

    BINDINGS = [
        Binding("escape", "quit", "Quit"),
        Binding("h", "show_help", "Help"),
        Binding("s", "save_config", "Save"),
    ]

    CSS_PATH = "styles/base.css"

    def __init__(self, config_data: Dict[str, Any], save_callback: Callable):
        super().__init__()
        self.config_data = config_data
        self.current_row = None
        self.save = save_callback

    def compose(self) -> ComposeResult:
        with ScrollableContainer():
            yield DataTable(cursor_type="row")
        yield Footer()

    def action_save_config(self) -> None:
        self.save(self.config_data)
        self.notify("Configuration saved successfully")

    def action_show_help(self) -> None:
        self.notify(self.get_help_text())

    def get_help_text(self) -> str:
        return "Help: Press 'h' for help, 's' to save, Escape to quit"


class EnvConfigEditor(ConfigEditorBase):
    """Editor for environment variables"""

    BINDINGS = [
        *ConfigEditorBase.BINDINGS,
        Binding("space", "toggle_value", "Toggle boolean/Edit string"),
        Binding("enter", "edit_value", "Edit Value"),
    ]

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Variable", "Value")
        self.refresh_table()

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for key, value in self.config_data.items():
            if isinstance(value, bool):
                display_value = "✓" if value else "✗"
            else:
                display_value = str(value)
            table.add_row(key, display_value)

    def action_toggle_value(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_coordinate is None:
            return

        row = table.cursor_coordinate.row
        key = list(self.config_data.keys())[row]
        value = self.config_data[key]

        if isinstance(value, bool):
            self.config_data[key] = not value
            self.refresh_table()
            table.move_cursor(row=row)
        else:
            self.action_edit_value()

    def action_edit_value(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_coordinate is None:
            return

        row = table.cursor_coordinate.row
        key = list(self.config_data.keys())[row]
        value = self.config_data[key]

        if not isinstance(value, bool):
            self.push_screen(EditValueScreen(key, str(value)))

    @on(EditValueScreen.ValueChanged)
    def handle_value_changed(self, message: EditValueScreen.ValueChanged) -> None:
        """Handle value changes from the edit modal"""
        key = message.key
        value = message.value

        # Try to preserve the original type
        original_value = self.config_data[key]
        if isinstance(original_value, int):
            try:
                value = int(value)
            except ValueError:
                self.notify("Invalid integer value")
                return

        self.config_data[key] = value
        self.refresh_table()
        table = self.query_one(DataTable)
        table.move_cursor(row=list(self.config_data.keys()).index(key))


class ActivationConfigScreen(ModalScreen):
    """Modal screen for configuring generator activation settings"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Submit"),
    ]

    def __init__(self, generator_name: str, activation_fields: Dict[str, str]):
        super().__init__()
        self.generator_name = generator_name
        self.activation_fields = activation_fields
        self.field_inputs = {}

    def compose(self) -> ComposeResult:
        with Static(id="dialog"):
            yield Static(f"Configure {self.generator_name}", id="title")
            for field_name, field_type in self.activation_fields.items():
                yield Static(field_name.title())
                input_widget = Input(
                    placeholder=f"Enter {field_name}",
                    password=field_type == "password",
                    id=f"input-{field_name}"
                )
                self.field_inputs[field_name] = input_widget
                yield input_widget
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        # Focus the first input field
        if self.field_inputs:
            first_field = next(iter(self.field_inputs.values()))
            first_field.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            self.save_config()
        else:
            self.app.pop_screen()

    def save_config(self) -> None:
        config_values = {
            field_name: self.query_one(f"#input-{field_name}").value
            for field_name in self.activation_fields
        }
        self.app.post_message(self.ActivationConfigured(config_values))
        self.app.pop_screen()

    class ActivationConfigured(Message):
        def __init__(self, config_values: Dict[str, str]):
            self.config_values = config_values
            super().__init__()


class DeactivationConfirmScreen(ModalScreen):
    """Modal screen for confirming generator deactivation"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Submit"),
    ]

    def compose(self) -> ComposeResult:
        with Static(id="dialog"):
            yield Static("Confirm Deactivation", id="title")
            yield Static("Are you sure you want to deactivate this generator? This will also disable it.")
            with Horizontal():
                yield Button("Yes", variant="error", id="confirm")
                yield Button("No", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm":
            self.app.post_message(self.DeactivationConfirmed())
        self.app.pop_screen()

    class DeactivationConfirmed(Message):
        pass


class GeneratorConfigEditor(ConfigEditorBase):
    """Editor for generator configurations"""

    BINDINGS = [
        *ConfigEditorBase.BINDINGS,
        Binding("space,enter", "toggle_enabled", "Toggle Enabled"),
        Binding("shift+up", "move_up", "Move Up"),
        Binding("shift+down", "move_down", "Move Down"),
        Binding("a", "toggle_activation", "Toggle Activation"),
    ]

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Name", "Enabled", "Activation", "Is Local")
        self.refresh_table()

    def refresh_table(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        for gen in self.config_data:
            enabled_status = "✓" if gen["enabled"] else "✗"
            activation_status = "🔒" if gen["activated"] else "⭕"
            is_local = "✓" if gen.get("is_local", False) else "✗"
            table.add_row(gen["name"], enabled_status, activation_status, is_local)

    def action_toggle_enabled(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            if 0 <= row < len(self.config_data):
                if not self.config_data[row]["activated"]:
                    self.notify("Cannot enable: Generator is not activated!")
                    return
                self.config_data[row]["enabled"] = not self.config_data[row]["enabled"]
                self.refresh_table()
                table.move_cursor(row=row)

    def action_toggle_activation(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            if 0 <= row < len(self.config_data):
                generator = self.config_data[row]

                if generator["activated"]:
                    # Show deactivation confirmation
                    self.push_screen(DeactivationConfirmScreen())
                else:
                    # Show activation configuration if required
                    activation_fields = generator.get("activation_fields", {})
                    if activation_fields:
                        self.push_screen(ActivationConfigScreen(generator["name"], activation_fields))
                    else:
                        self._activate_generator(row, {})

    @on(DeactivationConfirmScreen.DeactivationConfirmed)
    def handle_deactivation_confirmed(self, _: Message) -> None:
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        if row is not None:
            self.config_data[row]["activated"] = False
            self.config_data[row]["enabled"] = False
            if "activation_config" in self.config_data[row]:
                del self.config_data[row]["activation_config"]
            self.refresh_table()
            table.move_cursor(row=row)

    @on(ActivationConfigScreen.ActivationConfigured)
    def handle_activation_configured(self, message: ActivationConfigScreen.ActivationConfigured) -> None:
        table = self.query_one(DataTable)
        row = table.cursor_coordinate.row
        if row is not None:
            self._activate_generator(row, message.config_values)

    def _activate_generator(self, row: int, config_values: Dict[str, str]) -> None:
        self.config_data[row]["activated"] = True
        if config_values:
            self.config_data[row]["activation_config"] = config_values
        self.refresh_table()
        table = self.query_one(DataTable)
        table.move_cursor(row=row)

    def action_move_up(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            if row > 0:
                self.config_data[row], self.config_data[row - 1] = \
                    self.config_data[row - 1], self.config_data[row]
                self.refresh_table()
                table.move_cursor(row=row - 1)

    def action_move_down(self) -> None:
        table = self.query_one(DataTable)
        if table.cursor_coordinate is not None:
            row = table.cursor_coordinate.row
            if row < len(self.config_data) - 1:
                self.config_data[row], self.config_data[row + 1] = \
                    self.config_data[row + 1], self.config_data[row]
                self.refresh_table()
                table.move_cursor(row=row + 1)
