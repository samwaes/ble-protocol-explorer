from medisana_bs430.decoder import decode_feature_frame, decode_weight_frame


def test_capture_1649_decodes_correctly():
    weight = bytes.fromhex("1D A4 1F 00 FE 75 FA 20 1F 0D 13 00 FF 01 09 00 00 00 00")
    feature = bytes.fromhex("6F 75 FA 20 1F 01 B9 0A C8 F0 69 F2 79 F1 20 F0 00 00 00")
    measurement = decode_weight_frame(weight)
    decode_feature_frame(feature, measurement)
    assert measurement.weight_kg == 81.0
    assert measurement.scale_timestamp_utc == "2026-07-20T14:49:25+00:00"
    assert measurement.body_fat_percent == 20.0
    assert measurement.body_water_percent == 61.7
    assert measurement.muscle_percent == 37.7
    assert measurement.bone_mass_kg == 3.2
    assert measurement.impedance_ohm == 487.7
    assert measurement.profile_id_candidate == 1
