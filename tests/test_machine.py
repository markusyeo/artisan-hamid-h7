from src.machine import Machine


def test_decode_valid_message() -> None:
    machine = Machine()
    assert machine.decode_message(b"[25.5,100.2,50,75]") is True
    assert machine.environment_temperature == 25.5
    assert machine.bean_temperature == 100.2
    assert machine.heater_value == 50
    assert machine.fan_value == 75
    assert machine.last_telemetry_time > 0


def test_decode_message_with_nul_padding() -> None:
    machine = Machine()
    assert machine.decode_message(b"[25.5,100.2,50,75]\x00\x00") is True
    assert machine.fan_value == 75


def test_decode_invalid_message_leaves_state_untouched() -> None:
    machine = Machine()
    machine.decode_message(b"[25.5,100.2,50,75]")
    assert machine.decode_message(b"garbage") is False
    assert machine.decode_message(b"[1,2,3]") is False
    assert machine.bean_temperature == 100.2
    assert machine.fan_value == 75
