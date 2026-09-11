# `setattr` — What It Is and Where We Use It

## 1. The one-line definition

`setattr(obj, name, value)` sets an attribute on an object when the
attribute's **name is only known at runtime** (a string in a variable).

```python
setattr(user, "balance", 25.0)
# is exactly equivalent to:
user.balance = 25.0
```

Signature: `setattr(object, name, value) -> None`

With dot syntax the attribute name is hardcoded. With `setattr` it can come
from a loop variable, a function argument, a dict key, user input, etc.
That is the entire reason it exists.

## 2. The family: `getattr` / `hasattr` / `delattr`

| Builtin                  | Dot-syntax equivalent | Returns   |
| ------------------------ | --------------------- | --------- |
| `setattr(o, n, v)`       | `o.n = v`             | `None`    |
| `getattr(o, n)`          | `o.n`                 | the value |
| `getattr(o, n, default)` | `o.n` or `default`    | the value |
| `hasattr(o, n)`          | `try: o.n`            | `bool`    |
| `delattr(o, n)`          | `del o.n`             | `None`    |

Example:

```python
class Customer:
    def __init__(self):
        self.balance = 0.0

c = Customer()

field = "balance"          # decided at runtime, e.g. from an API payload
setattr(c, field, 50.0)    # c.balance = 50.0
print(getattr(c, field))   # 50.0
print(hasattr(c, "phone")) # False
```

## 3. Every `setattr` in this repo

There are two production uses (plus one `monkeypatch.setattr` in tests,
which is pytest's tool for temporarily patching attributes — unrelated).

### 3a. `src/database/workstations/update.py:48-49`

```python
for field, value in values.items():
    setattr(workstation, field, value)
```

`values` is a dict built from whichever update fields the caller actually
passed (`name`, `hourly_rate`, `is_active`). Instead of writing one
assignment per field:

```python
# without setattr you would need:
if "name" in values:
    workstation.name = values["name"]
if "hourly_rate" in values:
    workstation.hourly_rate = values["hourly_rate"]
# ... repeated for every field, forever
```

the loop applies any combination with two lines. Adding a new updatable
column later means adding it to the dict-building code only — the loop
does not change.

Because `workstation` is a SQLAlchemy model, each `setattr` marks that
column dirty, so the following `db.commit()` persists exactly the changed
columns.

### 3b. `src/database/customers/permissions/crud.py:37-39`

```python
for field in FLAG_FIELDS:
    if field in flags and flags[field] is not None:
        setattr(row, field, bool(flags[field]))
```

`FLAG_FIELDS` is the allow-list of permission columns:

```python
FLAG_FIELDS = (
    "can_manage_admins",
    "can_manage_users",
    "can_manage_workstations",
    "can_manage_billing",
    "read_only_billing",
)
```

`PUT /users/{id}/admin` accepts a partial payload like
`{"permissions": {"can_manage_users": true}}`. The loop sets only the
flags present in the request and ignores everything else — clients cannot
sneak in an arbitrary attribute because any key not in `FLAG_FIELDS` is
skipped. That allow-list is what makes this `setattr` safe (see §5).

## 4. Runnable example

```python
FLAG_FIELDS = ("can_manage_users", "can_manage_billing")

class Row:
    can_manage_users = False
    can_manage_billing = False

def set_flags(row, **flags):
    for field in FLAG_FIELDS:          # allow-list, not raw user input
        if field in flags and flags[field] is not None:
            setattr(row, field, bool(flags[field]))
    return row

row = set_flags(Row(), can_manage_users=True, is_superadmin=True)
print(row.can_manage_users)   # True  (applied)
print(row.can_manage_billing) # False (untouched)
print(hasattr(row, "is_superadmin"))  # False (blocked by allow-list)
```

## 5. Gotchas

1. **No allow-list = arbitrary attribute injection.** Never do
   `setattr(obj, user_supplied_string, value)` directly. Always loop over
   a fixed tuple of permitted names (both repo usages do this).
2. **Typos fail silently.** `setattr(row, "can_manage_user", True)`
   (missing the `s`) creates a brand-new useless attribute instead of
   raising — dot assignment has the same behavior. Tests that read the
   value back catch this.
3. **It respects descriptors.** On SQLAlchemy models `setattr` triggers
   change tracking; on classes with `@property` setters it calls the
   setter; on `__slots__` classes it raises `AttributeError` for unlisted
   names. It is real assignment, not dict hacking.
4. **Returns `None`.** `x = setattr(...)` assigns `None` to `x` — a
   common beginner bug.
