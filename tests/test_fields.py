"""Label alignment by meaning, and value normalisation, are the core of the task.

The SI and the BL name the same thing differently ("Port of Loading" vs "Load Port").
These tests pin the requirement: alignment is by meaning, never by header string.
"""

import pytest

from dock.fields import FIELDS, canonical_field, values_match


@pytest.mark.parametrize(
    ("label", "field"),
    [
        ("Shipper", "shipper"),
        ("SHIPPER", "shipper"),
        ("Shipper/Exporter", "shipper"),
        ("Shipper (Principal or Seller)", "shipper"),
        ("Exporter", "shipper"),
        ("Consignee", "consignee"),
        ("CONSIGNEE", "consignee"),
        ("Consignee (Non-Negotiable)", "consignee"),
        ("To the Order of", "consignee"),
        ("Notify", "notify_party"),
        ("Notify Party", "notify_party"),
        ("NOTIFY PARTY", "notify_party"),
        ("Notify Party/Intermediate Consignee", "notify_party"),
        ("Port of Loading", "port_of_loading"),
        ("Port of Loading (POL)", "port_of_loading"),
        ("POL", "port_of_loading"),
        ("Load Port", "port_of_loading"),
        ("PORT OF LOADING", "port_of_loading"),
        ("Port of Discharge", "port_of_discharge"),
        ("Port of Discharge (POD)", "port_of_discharge"),
        ("POD", "port_of_discharge"),
        ("Discharge Port", "port_of_discharge"),
        ("No. of Containers", "container_count"),
        ("No. of Containers or Packages", "container_count"),
        ("Total Containers", "container_count"),
        ("Container Count", "container_count"),
        ("Gross Weight", "gross_weight_kg"),
        ("Gross Weight (KG)", "gross_weight_kg"),
        ("Gross Wt (kgs)", "gross_weight_kg"),
        ("TOTAL GROSS WEIGHT", "gross_weight_kg"),
        ("TOTAL Gross Wt (kgs)", "gross_weight_kg"),
    ],
)
def test_known_labels_align_to_their_meaning(label: str, field: str) -> None:
    assert canonical_field(label) == field


def test_cjk_annotated_labels_align() -> None:
    """Real documents carry bilingual headers; the CJK gloss must not defeat alignment."""
    assert canonical_field("Gross Weight毛重(KGS)") == "gross_weight_kg"
    assert canonical_field("Shipper (Principal or Seller) (发货人)") == "shipper"
    assert canonical_field("PORT OF LOADING (装货港)") == "port_of_loading"
    assert canonical_field("B/L NO.(提单号)") is None


def test_net_weight_is_not_gross_weight() -> None:
    """The documents carry a NET WEIGHT line as a decoy. Matching it would be a false alarm."""
    assert canonical_field("NET WEIGHT") is None
    assert canonical_field("Net Wt (kgs)") is None


def test_unrelated_labels_do_not_align() -> None:
    for label in ("HS Code", "Freight", "Booking Ref", "Voyage", "Commodity", "OC No."):
        assert canonical_field(label) is None


def test_there_are_exactly_seven_comparable_fields() -> None:
    assert FIELDS == (
        "shipper",
        "consignee",
        "notify_party",
        "port_of_loading",
        "port_of_discharge",
        "container_count",
        "gross_weight_kg",
    )


class TestValuesMatch:
    def test_port_locode_suffix_is_noise(self) -> None:
        assert values_match("port_of_loading", "NHAVA SHEVA, INDIA", "NHAVA SHEVA, INDIA (INNSA)")
        assert values_match("port_of_discharge", "CONAKRY, GUINEA (GNCKY)", "CONAKRY, GUINEA")

    def test_port_locode_does_not_mask_a_different_city(self) -> None:
        """Both sides may carry the same locode while the city text differs - still a defect."""
        assert not values_match(
            "port_of_discharge", "MOMBASA, KENYA (KEMBA)", "TUTICORIN, INDIA (KEMBA)"
        )

    def test_descriptive_parenthetical_is_kept(self) -> None:
        assert not values_match(
            "port_of_loading",
            "PORT KLANG (WESTPORT), MALAYSIA (MYPKG)",
            "SINGAPORE, SINGAPORE (MYPKG)",
        )

    def test_gross_weight_compares_numerically(self) -> None:
        assert values_match("gross_weight_kg", "21,577 KG", "21577")
        assert values_match("gross_weight_kg", "243,588", "243,588 KGS")
        assert not values_match("gross_weight_kg", "21,114 KG", "23,114 KG")

    def test_container_count_compares_count_and_type(self) -> None:
        assert values_match("container_count", "6 x 40'HC", "6 X 40'HC")
        assert not values_match("container_count", "6 x 20'GP", "5 x 20'GP")
        assert not values_match("container_count", "6 x 40'HC", "6 x 20'GP")

    def test_party_names_ignore_case_and_spacing(self) -> None:
        assert values_match("shipper", "APRIL FAR EAST (M) SDN BHD", "April Far East (M)  Sdn Bhd")
        assert not values_match("consignee", "EAST BRIGHT FZ-LLC", "UAB NOVAKOPA")
