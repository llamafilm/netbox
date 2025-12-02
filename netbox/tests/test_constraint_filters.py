"""
Test constraint filtering with invert support for negated constraints.
"""
from django.test import TestCase

from dcim.models import Site, Region
from utilities.permissions import qs_filter_from_constraints


class ConstraintFiltersTestCase(TestCase):
    """
    Tests for qs_filter_from_constraints function with backwards compatibility.
    """

    @classmethod
    def setUpTestData(cls):
        # Create test regions and sites
        cls.region_1 = Region.objects.create(name='Americas', slug='americas')
        cls.region_2 = Region.objects.create(name='EMEA', slug='emea')

        cls.site_1 = Site.objects.create(
            name='NYC1',
            slug='nyc1',
            region=cls.region_1,
            status='active'
        )
        cls.site_2 = Site.objects.create(
            name='NYC2',
            slug='nyc2',
            region=cls.region_1,
            status='active'
        )
        cls.site_3 = Site.objects.create(
            name='LON1',
            slug='lon1',
            region=cls.region_2,
            status='deprecated'
        )
        cls.site_4 = Site.objects.create(
            name='Site Global',
            slug='site-global',
            region=None,
            status='active'
        )

    def test_legacy_format_simple_filter(self):
        """Test legacy format with simple field filter."""
        constraints = [{"status": "active"}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        self.assertIn(self.site_1, results)
        self.assertIn(self.site_2, results)
        self.assertNotIn(self.site_3, results)
        self.assertIn(self.site_4, results)

    def test_legacy_format_null_filter(self):
        """Test legacy format with explicit isnull lookup."""
        constraints = [{"region__isnull": True}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        self.assertNotIn(self.site_1, results)
        self.assertNotIn(self.site_2, results)
        self.assertNotIn(self.site_3, results)
        self.assertIn(self.site_4, results)

    def test_legacy_format_multiple_fields(self):
        """Test legacy format with multiple fields (AND operation)."""
        constraints = [{"status": "active", "region__name": "Americas"}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        self.assertIn(self.site_1, results)
        self.assertIn(self.site_2, results)
        self.assertNotIn(self.site_3, results)
        self.assertNotIn(self.site_4, results)

    def test_new_format_include_simple(self):
        """Test inverted constraint with single field."""
        constraints = [{"status": "active", "invert": True}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Should match all sites that are NOT active
        self.assertNotIn(self.site_1, results)
        self.assertNotIn(self.site_2, results)
        self.assertIn(self.site_3, results)
        self.assertNotIn(self.site_4, results)

    def test_new_format_exclude_simple(self):
        """Test inverted constraint with multiple fields (AND)."""
        constraints = [{"status": "active", "region__name": "Americas", "invert": True}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Should match all sites that are NOT (active AND in Americas)
        # Site 1,2 are active AND in Americas - excluded
        # Site 3 is not active, so it's included
        # Site 4 is active but not in Americas, so it's included
        self.assertNotIn(self.site_1, results)
        self.assertNotIn(self.site_2, results)
        self.assertIn(self.site_3, results)
        self.assertIn(self.site_4, results)

    def test_new_format_exclude_null(self):
        """Test inverted null constraint (require NOT NULL)."""
        constraints = [{"region__isnull": True, "invert": True}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Should match all sites where region is NOT null
        self.assertIn(self.site_1, results)
        self.assertIn(self.site_2, results)
        self.assertIn(self.site_3, results)
        self.assertNotIn(self.site_4, results)

    def test_empty_constraint(self):
        """Test empty constraint dict."""
        constraints = [{}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Empty constraint should match all sites
        self.assertEqual(results.count(), Site.objects.count())

    def test_invert_empty_constraint(self):
        """Test inverted empty constraint (matches nothing)."""
        constraints = [{"invert": True}]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Inverted empty constraint negates matching all (becomes match none)
        self.assertEqual(results.count(), 0)

    def test_multiple_constraints_or_operation(self):
        """Test multiple constraints combined with OR operation."""
        constraints = [
            {"status": "deprecated"},
            {"region__name": "Americas"}
        ]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Should match deprecated sites OR sites in Americas
        self.assertIn(self.site_1, results)
        self.assertIn(self.site_2, results)
        self.assertIn(self.site_3, results)

    def test_mixed_inverted_and_normal(self):
        """Test constraints mixing inverted and normal constraints."""
        constraints = [
            {"status": "active"},  # Normal: match active sites
            {"region__name": "EMEA", "invert": True}  # Inverted: match sites NOT in EMEA
        ]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Should match (status=active) OR (NOT in EMEA)
        # Site 1: active AND in Americas (not EMEA) - matches via invert
        # Site 2: active AND in Americas (not EMEA) - matches via invert
        # Site 3: deprecated AND in EMEA - doesn't match via status, doesn't match via invert
        # Site 4: active AND no region (not EMEA) - matches via both
        self.assertIn(self.site_1, results)
        self.assertIn(self.site_2, results)
        self.assertNotIn(self.site_3, results)
        self.assertIn(self.site_4, results)

    def test_null_constraint_returns_all(self):
        """Test that null constraint allows all objects."""
        constraints = [
            None,
            {"status": "deprecated"}
        ]
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Null constraint should permit all
        self.assertEqual(results.count(), Site.objects.count())

    def test_empty_constraints_list(self):
        """Test empty constraints list."""
        constraints = []
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        # Empty constraints should match nothing
        self.assertEqual(results.count(), 0)

    def test_legacy_constraint_format_is_valid(self):
        """Test that legacy flat dict format still works."""
        constraints = [{"name": "TestSite"}]
        # Create a site to test against
        region = Region.objects.create(name='Test', slug='test')
        site = Site.objects.create(
            name='TestSite',
            slug='test-site',
            region=region,
            status='active'
        )
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        self.assertIn(site, results)

    def test_legacy_constraint_with_lookups(self):
        """Test legacy format with Django lookup expressions."""
        constraints = [{"name__startswith": "Test"}]
        # Create a site to test against
        region = Region.objects.create(name='Test2', slug='test2')
        site = Site.objects.create(
            name='TestSite2',
            slug='test-site2',
            region=region,
            status='active'
        )
        q = qs_filter_from_constraints(constraints)
        results = Site.objects.filter(q)

        self.assertIn(site, results)

    def test_legacy_vs_inverted_format_difference(self):
        """Test that legacy and inverted format produce different results."""
        region = Region.objects.create(name='Test Americas', slug='test-americas')
        site = Site.objects.create(
            name='TestSite',
            slug='test-site',
            region=region,
            status='active'
        )

        # Legacy: match where status=active
        legacy_constraints = [{"status": "active"}]
        q_legacy = qs_filter_from_constraints(legacy_constraints)
        results_legacy = Site.objects.filter(q_legacy)

        # Inverted: match where NOT (status=active)
        inverted_constraints = [{"status": "active", "invert": True}]
        q_inverted = qs_filter_from_constraints(inverted_constraints)
        results_inverted = Site.objects.filter(q_inverted)

        # Results should be opposite
        self.assertIn(site, results_legacy)
        self.assertNotIn(site, results_inverted)
