# Negated Permission Constraints Implementation

## Summary

This implementation adds support for explicit `include`/`exclude` constraint syntax to NetBox permission constraints, enabling clearer negation logic while maintaining full backwards compatibility with existing flat dictionary constraints.

## Changes Made

### 1. Core Implementation: `/netbox/utilities/permissions.py`

Updated `qs_filter_from_constraints()` to:
- Support both legacy flat dictionary format and new explicit `include`/`exclude` format
- Convert constraints to Django Q objects for use in querysets
- Handle None values as `__isnull` checks automatically
- Support full Django ORM lookup syntax in both `include` and `exclude` dictionaries
- Use an internal `_constraint_to_q()` helper function for constraint parsing

The function detects the format automatically:
- If the constraint dict contains `include` or `exclude` keys, it uses the new format
- Otherwise, it treats the entire dict as legacy format (equivalent to `include`)

**Key Features:**
- ✅ Full backwards compatibility with legacy constraints
- ✅ Explicit negation via `exclude` dict (clearer than custom `__n` suffix)
- ✅ Mixed constraints within a single permission
- ✅ Token replacement (e.g., `$user`) works in both formats
- ✅ Support for all Django ORM lookup expressions
- ✅ Logic kept internal to avoid public API expansion

### 2. Form Updates: `/netbox/users/forms/model_forms.py`

Updated the `constraints` field help text to document:
- Support for both legacy and new formats
- That multiple constraint objects are OR'd together
- Reference to include/exclude syntax

### 3. Documentation Updates: `/docs/administration/permissions.md`

Added comprehensive documentation including:
- Explanation of new `include`/`exclude` syntax
- When to use each format
- Null value handling in exclusions
- Real-world use case example: protecting imported data from edits
- Updated constraint definition table with new examples

### 4. Tests: `/netbox/tests/test_constraint_filters.py`

Created comprehensive test suite covering:
- **Legacy format tests**: Simple filters, null checks, multiple fields (AND)
- **New format tests**: Include-only, exclude-only, combined include+exclude
- **Backwards compatibility tests**: Equivalence between legacy and new formats
- **Multiple constraint tests**: OR semantics across permissions
- **Mixed format tests**: Same permission using both legacy and new formats
- **Edge cases**: Empty constraints, null constraints, token replacement

Test cases include:
- `test_legacy_format_simple_filter()` - Basic legacy constraint
- `test_legacy_format_null_filter()` - Null checking with legacy format
- `test_legacy_format_multiple_fields()` - AND semantics in legacy format
- `test_new_format_include_simple()` - New format with include only
- `test_new_format_exclude_simple()` - New format with exclude only
- `test_new_format_exclude_null()` - Excluding null values (require NOT NULL)
- `test_new_format_include_and_exclude()` - Combined include and exclude
- `test_multiple_constraints_or_operation()` - OR across multiple constraints
- `test_mixed_legacy_and_new_format()` - Both formats in same permission
- `test_legacy_vs_new_format_equivalence()` - Proof of backwards compatibility

## Usage Examples

### Example 1: Protect Imported Data (Original Use Case)

Create two permissions for editing Prefixes:

**Permission 1: Edit Prefixes in Global VRF**
```json
{
  "include": {"vrf_id": null}
}
```

**Permission 2: Edit Prefixes in Non-Global VRFs**
```json
{
  "exclude": {"vrf_id": null}
}
```

This allows users to edit either imported prefixes (global VRF) OR manually created prefixes (non-global VRFs) based on which permissions they have.

### Example 2: Complex Negation

```json
{
  "include": {"status": "active", "region__name": "Americas"},
  "exclude": {"deprecated": true}
}
```

Matches: Active objects in the Americas region that are not deprecated.

### Example 3: Legacy Format (Still Works)

```json
{
  "status": "active",
  "role": "testing"
}
```

Equivalent to:
```json
{
  "include": {"status": "active", "role": "testing"}
}
```

## Backwards Compatibility

✅ **100% backwards compatible** - No migration required

- All existing permission constraints continue to work unchanged
- Legacy flat dictionary format is automatically detected and handled
- Can mix old and new formats in the same permission system
- No database changes required
- Gradual migration path: administrators can update constraints to new format at their own pace

## Constraint Logic Summary

### Within a Single Constraint Dict

- **Legacy format**: All keys AND together
  ```python
  {"status": "active", "region": "1"} 
  # => Q(status="active") & Q(region=1)
  ```

- **New format with include**: All include keys AND together
  ```python
  {"include": {"status": "active", "region": "1"}} 
  # => Q(status="active") & Q(region=1)
  ```

- **New format with exclude**: All exclude keys AND together as negations
  ```python
  {"exclude": {"status": "active", "region": "1"}} 
  # => ~Q(status="active") & ~Q(region=1)
  ```

- **New format with both**: Include AND Exclude
  ```python
  {"include": {"status": "active"}, "exclude": {"deprecated": true}} 
  # => Q(status="active") & ~Q(deprecated=true)
  ```

### Across Multiple Constraints in a Permission

Multiple constraint dicts are OR'd together:
```python
[
  {"status": "active"},
  {"region": "2"}
]
# => Q(status="active") | Q(region=2)
```

### Across Multiple Permissions

When a user has multiple permissions for the same object type, they are also OR'd:
- Permission A: `{"vrf_id": null}`
- Permission B: `{"vrf_id__n": null}` (using new format: `{"exclude": {"vrf_id": null}}`)
- Result: User can edit anything (all objects match at least one permission)

## Testing Instructions

To run the new test suite:

```bash
cd /path/to/netbox
python manage.py test netbox.tests.test_constraint_filters -v 2
```

Expected output: All tests pass with both legacy and new formats producing correct results.

## Migration/Admin Guidance

### For Existing Administrators

1. **No immediate action required** - All existing constraints work as-is
2. **Gradual adoption** - Update constraints to new format when creating new permissions or modifying existing ones
3. **Testing recommended** - Before deploying complex permission schemes, test thoroughly in a staging environment
4. **Mixed formats are OK** - You can use both legacy and new formats simultaneously

### Best Practices

- Use legacy format (`{"field": value}`) for simple positive constraints
- Use new format `{"include": {...}, "exclude": {...}}` for complex rules with negations
- Document permission purposes in the `description` field
- Test permission combinations before deployment
- Use `$user` token for user-scoped constraints (e.g., only edit own journal entries)

### Example Permission Setup

For the BloxOne DDI automation use case:

1. Create Permission: "Edit Global VRF Prefixes"
   - Objects: Prefix
   - Actions: change, delete
   - Constraints: `{"include": {"vrf_id": null}}`
   - Assigned to: Administrative group

2. Create Permission: "Edit Non-Global VRF Prefixes"
   - Objects: Prefix
   - Actions: change, delete
   - Constraints: `{"exclude": {"vrf_id": null}}`
   - Assigned to: Regular users

3. Result: Regular users can modify prefixes in air-gapped networks but not the global/imported VRF

## Files Modified

1. `/netbox/utilities/permissions.py` - Updated `qs_filter_from_constraints` with inline constraint parsing logic
2. `/netbox/users/forms/model_forms.py` - Form help text updates
3. `/docs/administration/permissions.md` - Admin documentation
4. `/netbox/tests/test_constraint_filters.py` - New test suite

## Security Considerations

- Constraints are validated at permission creation time (existing behavior preserved)
- No changes to permission evaluation logic security model
- Negation is explicit and clear, reducing configuration errors
- All constraint values are parameterized (no SQL injection risk)
