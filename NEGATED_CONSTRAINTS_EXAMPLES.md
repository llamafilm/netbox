# Negated Permission Constraints - Usage Examples

## Your Original Use Case

**Scenario:** Prefixes in the global VRF are imported from BloxOne DDI. You want users to be able to edit prefixes in non-global VRFs (air-gapped networks) but NOT the global VRF prefixes.

### Before This Feature (Workaround)

You had to create confusing or inaccurate permission descriptions, or use workarounds:

```json
// Option 1: Only allow specific non-global VRFs (not scalable)
{
  "vrf_id__in": [1, 2, 3, 4, 5]  // Hard-coded list of VRF IDs
}

// Option 2: No good way to say "everything except VRF 0"
```

### After This Feature (Clean Solution)

**Permission 1: Edit Global VRF Prefixes (for admins only)**
```json
{
  "include": {"vrf_id": null}
}
```
- Clearly states: Match prefixes where vrf_id is NULL (the global VRF)
- Assign to: Administrators/Automation accounts

**Permission 2: Edit Non-Global VRF Prefixes (for regular users)**
```json
{
  "exclude": {"vrf_id": null}
}
```
- Clearly states: Match all prefixes EXCEPT those where vrf_id is NULL
- Assign to: Regular users

**Result:** Complete coverage with clear intent ✅

---

## Additional Examples

### Example 1: Restrict to Active Sites in Specific Region (with Exceptions)

**Scenario:** Users can edit sites in the Americas region that are active, but not if they're marked as 'deprecated'

```json
{
  "include": {
    "status": "active",
    "region__name": "Americas"
  },
  "exclude": {
    "deprecated": true
  }
}
```

Equivalent to SQL:
```sql
WHERE status = 'active' 
  AND region.name = 'Americas' 
  AND deprecated != true
```

---

### Example 2: Import Lock Pattern

**Scenario:** Prevent editing of any object that was imported (has a timestamp in the `imported_at` field)

```json
{
  "exclude": {"imported_at__isnull": false}
}
```

This matches all objects EXCEPT those with a non-null `imported_at` timestamp.

---

### Example 3: Protect System Objects

**Scenario:** Users can edit everything except system-reserved prefixes

```json
{
  "exclude": {"name__startswith": "RESERVED_"}
}
```

---

### Example 4: Multiple Constraints with OR Logic

**Scenario:** Users can edit prefixes that are:
1. In the development VRF, OR
2. Not yet deployed AND not in the global VRF

```json
[
  {
    "include": {"vrf__name": "Development"}
  },
  {
    "include": {"status": "development"},
    "exclude": {"vrf_id": null}
  }
]
```

Matches any prefix that is either:
- In Development VRF, OR
- Has development status AND is not in the global VRF

---

### Example 5: Mixed Legacy and New Format (Backwards Compatible)

**Scenario:** Your permission system has both old and new constraints

```json
[
  {
    "status": "active"  // Legacy format - treated as include
  },
  {
    "include": {"region": 1},
    "exclude": {"deprecated": true}  // New format
  }
]
```

Works perfectly! NetBox auto-detects format and handles both.

---

## Comparison: Legacy vs. New Format

| Use Case | Legacy Format | New Format | Notes |
|----------|---------------|-----------|-------|
| Simple match | `{"status": "active"}` | `{"include": {"status": "active"}}` | Both work identically |
| Multiple AND | `{"status": "active", "vrf": 1}` | `{"include": {"status": "active", "vrf": 1}}` | Both work identically |
| Null check | `{"vrf_id": null}` | `{"include": {"vrf_id": null}}` | Both work identically |
| Simple negation | ❌ Not possible cleanly | `{"exclude": {"status": "inactive"}}` | New format wins |
| Complex negation | ❌ Requires workarounds | `{"include": {...}, "exclude": {...}}` | New format clear & clean |
| Mixed operators | ❌ Limited | `{"include": {...}, "exclude": {...}}` | New format excels |

---

## Null/Is Null Behavior

Both formats automatically convert None values to `__isnull` checks:

```json
// These are equivalent:
{"vrf_id": null}
{"vrf_id__isnull": true}

// Using new format:
{"include": {"vrf_id": null}}
{"include": {"vrf_id__isnull": true}}

// Excluding nulls (exclude from match = require NOT NULL):
{"exclude": {"vrf_id": null}}
// Equivalent to: Q(vrf_id__isnull=False) 
// Meaning: vrf_id is NOT null (vrf_id is required/populated)
```

---

## Token Replacement

The special `$user` token works in both formats:

```json
// Legacy format with token
{
  "created_by": "$user"
}

// New format with token
{
  "include": {"created_by": "$user"}
}

// New format with token and exclusions
{
  "include": {"created_by": "$user"},
  "exclude": {"archived": true}
}
```

At runtime, `$user` is replaced with the current user's ID.

---

## Real-World Permission Hierarchy for Data Automation

```python
# Permission 1: Admins can modify anything
{
  "name": "Admin: Full Prefix Access",
  "constraints": None,  # No constraints = full access
  "users": [admin_group]
}

# Permission 2: Automation service can only modify imported prefixes
{
  "name": "Automation: Edit Imported Prefixes",
  "constraints": {"include": {"source": "bloxone"}},
  "users": [automation_service_account]
}

# Permission 3: Users can modify manually created prefixes
{
  "name": "Users: Edit Manual Prefixes",
  "constraints": {"exclude": {"source": "bloxone"}},
  "users": [regular_users_group]
}
```

Result:
- ✅ Automation service can only touch BloxOne-imported prefixes
- ✅ Regular users can modify all other prefixes
- ✅ Admins have unrestricted access
- ✅ No overlap or conflicts
- ✅ Clear, maintainable permission structure

---

## Error Handling & Validation

Invalid constraints are caught at permission creation time:

```json
// ❌ Invalid: __isnull doesn't work with None
{"vrf_id__isnull": null}  // Error!

// ✅ Valid: __isnull works with True/False
{"vrf_id__isnull": true}

// ✅ Valid: Bare field name with None auto-converts to __isnull
{"vrf_id": null}
```

Error message clearly indicates which constraint is invalid and for which model.

---

## Migration Path

No migration needed! Start using the new format immediately:

1. **Phase 1:** Keep using legacy format in production (no changes needed)
2. **Phase 2:** Create new permissions using new format
3. **Phase 3:** Optionally update old permissions to new format as they're modified
4. **Phase 4:** Both formats coexist peacefully forever if needed

This means you can adopt the feature at your own pace, testing each new permission before deployment.
