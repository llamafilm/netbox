# Implementation Complete: Negated Permission Constraints

## Summary

Successfully implemented support for negated permission constraints in NetBox using an explicit `include`/`exclude` dict syntax. The feature is fully backwards compatible with existing constraints and requires no database migrations.

## What Was Changed

### 1. Core Logic: `/netbox/utilities/permissions.py`
- Enhanced `qs_filter_from_constraints()` to support both formats:
  - **Legacy format**: `{"field": value}` (flat dict) → auto-treated as `include`
  - **New format**: `{"include": {...}, "exclude": {...}}` (explicit)
- Added internal `_constraint_to_q()` helper function for constraint parsing
- Handles None values as `__isnull` checks automatically
- Full token replacement support (`$user`, etc.)
- No public API expansion (logic is internal)

### 2. User Documentation: `/netbox/users/forms/model_forms.py`
- Updated constraint field help text to document both formats
- Clear guidance for administrators

### 3. Admin Guide: `/docs/administration/permissions.md`
- Added full section on `Include/Exclude Constraints`
- Null value handling explained
- Use case examples including the BloxOne DDI scenario
- Updated constraint definition table with new examples

### 4. Test Suite: `/netbox/tests/test_constraint_filters.py`
- 14 comprehensive test cases covering:
  - Legacy format: simple filters, null checks, multiple fields
  - New format: include-only, exclude-only, combined
  - Multiple constraints: OR semantics
  - Mixed formats: both in same permission
  - Edge cases: empty constraints, null constraints
  - Backwards compatibility: legacy vs new equivalence

## Your Use Case: Solved ✅

**Scenario:** Protect imported prefixes (global VRF) from editing while allowing unrestricted access to manually created prefixes (non-global VRFs)

**Solution:**
```json
// Permission 1: Edit Global VRF Prefixes (admins/automation)
{"include": {"vrf_id": null}}

// Permission 2: Edit Non-Global VRF Prefixes (regular users)
{"exclude": {"vrf_id": null}}
```

**Result:** Clear, maintainable, explicit permissions with zero ambiguity.

## Key Benefits

1. **Backwards Compatible**: No changes needed to existing constraints
2. **Clear Intent**: Explicit `include`/`exclude` is self-documenting
3. **Flexible**: Supports complex filtering combinations
4. **Tested**: Comprehensive test coverage ensures reliability
5. **Documented**: Clear examples for administrators
6. **Minimal Changes**: Logic integrated into existing function, no new public APIs

## How It Works

```python
# Single constraint dict: fields AND together
{"status": "active", "region": "1"}
# OR equivalently in new format:
{"include": {"status": "active", "region": "1"}}

# Multiple constraint dicts: OR together
[
  {"status": "active"},
  {"region": "2"}
]
# Results in: (status=active) OR (region=2)

# New format with negation: include AND NOT exclude
{"include": {"status": "active"}, "exclude": {"deprecated": true}}
# Results in: (status=active) AND NOT (deprecated=true)
```

## Validation

The existing constraint validation in `ObjectPermissionForm.clean()` continues to work:
- Attempts to execute constraint against each model
- Clear error messages for invalid filters
- Works with both legacy and new formats

## Migration Path

**Immediate (No Action Required):**
- All existing permissions work unchanged
- No database migrations needed
- No configuration changes needed

**Gradual Adoption:**
1. Create new permissions using new format
2. Test in staging environment
3. Deploy with confidence
4. Update old permissions at your own pace (optional)
5. Both formats can coexist permanently

## Files Modified Summary

| File | Changes |
|------|---------|
| `/netbox/utilities/permissions.py` | Enhanced `qs_filter_from_constraints()` with inline parsing |
| `/netbox/users/forms/model_forms.py` | Updated help text documentation |
| `/docs/administration/permissions.md` | Added include/exclude section with examples |
| `/netbox/tests/test_constraint_filters.py` | New comprehensive test suite |
| `/NEGATED_CONSTRAINTS_IMPLEMENTATION.md` | Implementation details document |
| `/NEGATED_CONSTRAINTS_EXAMPLES.md` | Usage examples and real-world scenarios |

## Next Steps (Optional)

To use the new feature:

1. **Create a permission** in the NetBox UI or API with new format:
   ```json
   {
     "include": {"vrf_id": null},
     "exclude": {"deprecated": true}
   }
   ```

2. **Test it** against your use case in staging

3. **Deploy** with confidence - no database changes needed

4. **Document** your permission scheme in comments/description fields

## Security Notes

- All constraint values are parameterized (no SQL injection risk)
- Negation is explicit and clear (reduces configuration errors)
- Existing validation continues to work (catches invalid filters)
- No changes to permission evaluation security model
