"""Tests of Cloudvision utility methods."""
from unittest import skip
from unittest.mock import MagicMock, patch
from nautobot.dcim.models import DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Relationship, Role, Status, Tag
from nautobot.core.testing import TestCase
from nautobot_ssot.integrations.aristacv.utils import nautobot


class TestNautobotUtils(TestCase):
    """Test Nautobot utility methods."""

    databases = ("default", "job_logs")

    def test_verify_site_success(self):
        """Test the verify_site method for existing Site."""
        loc_type = LocationType.objects.get_or_create(name="Site")[0]
        test_site, _ = Location.objects.get_or_create(
            name="Test", location_type=loc_type, status=Status.objects.get(name="Active")
        )
        result = nautobot.verify_site(site_name="Test")
        self.assertEqual(result, test_site)

    def test_verify_site_fail(self):
        """Test the verify_site method for non-existing Site."""
        result = nautobot.verify_site(site_name="Test2")
        self.assertEqual(result.name, "Test2")
        self.assertTrue(isinstance(result, Location))

    def test_verify_device_type_object_success(self):
        """Test the verify_device_type_object for existing DeviceType."""
        new_dt, _ = DeviceType.objects.get_or_create(
            model="DCS-7150S-24", manufacturer=Manufacturer.objects.get(name="Arista")
        )
        result = nautobot.verify_device_type_object(device_type="DCS-7150S-24")
        self.assertEqual(result, new_dt)

    def test_verify_device_type_object_fail(self):
        """Test the verify_device_type_object for non-existing DeviceType."""
        result = nautobot.verify_device_type_object(device_type="DCS-7150S-24")
        self.assertEqual(result.model, "DCS-7150S-24")
        self.assertTrue(isinstance(result, DeviceType))

    def test_verify_device_role_object_success(self):
        """Test the verify_device_role_object method for existing DeviceRole."""
        new_dr, _ = Role.objects.get_or_create(name="Edge Router")
        result = nautobot.verify_device_role_object(role_name="Edge Router", role_color="ff0000")
        self.assertEqual(result, new_dr)

    def test_verify_device_role_object_fail(self):
        """Test the verify_device_role_object method for non-existing Role."""
        result = nautobot.verify_device_role_object(role_name="Distro Switch", role_color="ff0000")
        self.assertEqual(result.name, "Distro Switch")
        self.assertEqual(result.color, "ff0000")

    def test_verify_import_tag_success(self):
        """Test the verify_import_tag method for existing Tag."""
        new_tag, _ = Tag.objects.get_or_create(name="cloudvision_imported")
        result = nautobot.verify_import_tag()
        self.assertEqual(result, new_tag)

    def test_verify_import_tag_fail(self):
        """Test the verify_import_tag method for non-existing Tag."""
        result = nautobot.verify_import_tag()
        self.assertEqual(result.name, "cloudvision_imported")

    @skip("DLC App disabled")
    def test_get_device_version_dlc_success(self):
        """Test the get_device_version method pulling from Device Lifecycle app."""
        software_relation = Relationship.objects.get(label="Software on Device")

        mock_version = MagicMock()
        mock_version.source.version = MagicMock()
        mock_version.source.version = "1.0"

        mock_device = MagicMock()
        mock_device.get_relationships = MagicMock()
        mock_device.get_relationships.return_value = {"destination": {software_relation: [mock_version]}}

        result = nautobot.get_device_version(mock_device)
        self.assertEqual(result, "1.0")

    @skip("DLC App disabled")
    def test_get_device_version_dlc_fail(self):
        """Test the get_device_version method pulling from Device Lifecycle app but failing."""
        mock_device = MagicMock()
        mock_device.get_relationships = MagicMock()
        mock_device.get_relationships.return_value = {}

        result = nautobot.get_device_version(mock_device)
        self.assertEqual(result, "")

    def test_get_device_version_dlc_exception(self):
        """Test the get_device_version method pulling from the Device Custom Field."""
        mock_device = MagicMock()
        mock_device.custom_field_data = {"arista_eos": "1.0"}

        mock_import = MagicMock()
        mock_import.LIFECYCLE_MGMT = False

        with patch("nautobot_ssot.integrations.aristacv.utils.nautobot.LIFECYCLE_MGMT", mock_import.LIFECYCLE_MGMT):
            result = nautobot.get_device_version(mock_device)
        self.assertEqual(result, "1.0")

    @patch.dict(
        "nautobot_ssot.integrations.aristacv.constant.APP_SETTINGS",
        {
            "hostname_patterns": [r"(?P<site>\w{2,3}\d+)-(?P<role>\w+)-\d+"],
            "site_mappings": {"ams01": "Amsterdam"},
            "role_mappings": {"leaf": "leaf"},
        },
    )
    def test_parse_hostname(self):
        """Test the parse_hostname method."""
        host = "ams01-leaf-01"
        results = nautobot.parse_hostname(host)
        expected = ("ams01", "leaf")
        self.assertEqual(results, expected)

    @patch.dict(
        "nautobot_ssot.integrations.aristacv.constant.APP_SETTINGS",
        {
            "hostname_patterns": [r"(?P<site>\w{2,3}\d+)-.+-\d+"],
            "site_mappings": {"ams01": "Amsterdam"},
            "role_mappings": {},
        },
    )
    def test_parse_hostname_only_site(self):
        """Test the parse_hostname method with only site specified."""
        host = "ams01-leaf-01"
        results = nautobot.parse_hostname(host)
        expected = ("ams01", None)
        self.assertEqual(results, expected)

    @patch.dict(
        "nautobot_ssot.integrations.aristacv.constant.APP_SETTINGS",
        {
            "hostname_patterns": [r".+-(?P<role>\w+)-\d+"],
            "site_mappings": {},
            "role_mappings": {"leaf": "leaf"},
        },
    )
    def test_parse_hostname_only_role(self):
        """Test the parse_hostname method with only role specified."""
        host = "ams01-leaf-01"
        results = nautobot.parse_hostname(host)
        expected = (None, "leaf")
        self.assertEqual(results, expected)

    @patch.dict(
        "nautobot_ssot.integrations.aristacv.constant.APP_SETTINGS",
        {
            "hostname_patterns": [r"(?P<site>\w{2,3}\d+)-(?P<role>\w+)-\d+"],
            "site_mappings": {"ams01": "Amsterdam"},
        },
    )
    def test_get_site_from_map_success(self):
        """Test the get_site_from_map method with response."""
        results = nautobot.get_site_from_map("ams01")
        expected = "Amsterdam"
        self.assertEqual(results, expected)

    @patch.dict(
        "nautobot_ssot.integrations.aristacv.constant.APP_SETTINGS",
        {
            "hostname_patterns": [r"(?P<site>\w{2,3}\d+)-(?P<role>\w+)-\d+"],
            "site_mappings": {},
        },
    )
    def test_get_site_from_map_fail(self):
        """Test the get_site_from_map method with failed response."""
        results = nautobot.get_site_from_map("dc01")
        expected = None
        self.assertEqual(results, expected)

    @patch.dict(
        "nautobot_ssot.integrations.aristacv.constant.APP_SETTINGS",
        {
            "hostname_patterns": [r"(?P<site>\w{2,3}\d+)-(?P<role>\w+)-\d+"],
            "role_mappings": {"edge": "Edge Router"},
        },
    )
    def test_get_role_from_map_success(self):
        """Test the get_role_from_map method with response."""
        results = nautobot.get_role_from_map("edge")
        expected = "Edge Router"
        self.assertEqual(results, expected)

    @patch.dict(
        "nautobot_ssot.integrations.aristacv.constant.APP_SETTINGS",
        {
            "hostname_patterns": [r"(?P<site>\w{2,3}\d+)-(?P<role>\w+)-\d+"],
            "role_mappings": {},
        },
    )
    def test_get_role_from_map_fail(self):
        """Test the get_role_from_map method with failed response."""
        results = nautobot.get_role_from_map("rtr")
        expected = None
        self.assertEqual(results, expected)
