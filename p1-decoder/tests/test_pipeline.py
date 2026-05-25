import unittest

from p1_decoder._pipeline import ElectricityReading, Value


def electricity_reading(**overrides) -> ElectricityReading:
    values = {
        "timestamp": 1,
        "meter_id": Value(value="meter-1"),
        "import_t1_kwh": Value(value="100.000", unit="kWh"),
        "import_t2_kwh": Value(value="200.000", unit="kWh"),
        "export_t1_kwh": Value(value="10.000", unit="kWh"),
        "export_t2_kwh": Value(value="20.000", unit="kWh"),
        "active_tariff": Value(value="1"),
        "power_import_kw": Value(value="0.100", unit="kW"),
        "power_export_kw": Value(value="0.100", unit="kW"),
        "voltage_l1_v": Value(value="230.000", unit="V"),
        "voltage_l2_v": Value(value="231.000", unit="V"),
        "voltage_l3_v": Value(value="232.000", unit="V"),
        "current_l1_a": Value(value="1.000", unit="A"),
        "current_l2_a": Value(value="2.000", unit="A"),
        "current_l3_a": Value(value="3.000", unit="A"),
        "power_import_l1_kw": Value(value="0.100", unit="kW"),
        "power_import_l2_kw": Value(value="0.100", unit="kW"),
        "power_import_l3_kw": Value(value="0.100", unit="kW"),
        "power_export_l1_kw": Value(value="0.100", unit="kW"),
        "power_export_l2_kw": Value(value="0.100", unit="kW"),
        "power_export_l3_kw": Value(value="0.100", unit="kW"),
    }
    values.update(overrides)
    return ElectricityReading(**values)


class ElectricityReadingChangesTest(unittest.TestCase):
    def test_no_effective_change_returns_none(self):
        old = electricity_reading(timestamp=1)
        new = electricity_reading(
            timestamp=2,
            power_import_kw=Value(value="0.150", unit="kW"),
        )

        self.assertIsNone(new.only_changes(old, tolerance=0.1))

    def test_zero_instantaneous_power_is_a_change_inside_tolerance(self):
        old = electricity_reading(timestamp=1)
        new = electricity_reading(
            timestamp=2,
            power_import_kw=Value(value="0.000", unit="kW"),
            power_export_kw=Value(value="0.000", unit="kW"),
            power_import_l1_kw=Value(value="0.000", unit="kW"),
        )

        changed = new.only_changes(old, tolerance=0.1)

        self.assertIsNotNone(changed)
        self.assertEqual(changed.power_import_kw.value, "0.000")
        self.assertEqual(changed.power_export_kw.value, "0.000")
        self.assertEqual(changed.power_import_l1_kw.value, "0.000")

    def test_non_power_zero_inside_tolerance_is_not_a_change(self):
        old = electricity_reading(timestamp=1, current_l1_a=Value(value="0.100", unit="A"))
        new = electricity_reading(timestamp=2, current_l1_a=Value(value="0.000", unit="A"))

        self.assertIsNone(new.only_changes(old, tolerance=0.1))

    def test_change_above_tolerance_keeps_unchanged_fields_at_old_values(self):
        old = electricity_reading(timestamp=1, current_l1_a=Value(value="1.000", unit="A"))
        new = electricity_reading(
            timestamp=2,
            current_l1_a=Value(value="1.200", unit="A"),
            voltage_l1_v=Value(value="230.050", unit="V"),
        )

        changed = new.only_changes(old, tolerance=0.1)

        self.assertIsNotNone(changed)
        self.assertEqual(changed.current_l1_a.value, "1.200")
        self.assertEqual(changed.voltage_l1_v.value, "230.000")

    def test_to_dict_includes_phase_sums_and_signed_net(self):
        reading = electricity_reading(
            power_import_l1_kw=Value(value="0.000", unit="kW"),
            power_import_l2_kw=Value(value="0.000", unit="kW"),
            power_import_l3_kw=Value(value="0.279", unit="kW"),
            power_export_l1_kw=Value(value="0.000", unit="kW"),
            power_export_l2_kw=Value(value="0.761", unit="kW"),
            power_export_l3_kw=Value(value="0.000", unit="kW"),
        )

        data = reading.to_dict()

        self.assertEqual(data["power_import_phase_sum_kw"], 0.279)
        self.assertEqual(data["power_export_phase_sum_kw"], 0.761)
        self.assertEqual(data["power_net_kw"], -0.482)


if __name__ == "__main__":
    unittest.main()
