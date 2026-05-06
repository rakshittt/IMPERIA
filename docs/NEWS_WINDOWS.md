# IMPERIA News Windows

Stock news supports user-selectable windows:

| Public value | Normalized value |
| --- | --- |
| `today` | `today` |
| `past_day`, `1d` | `past_day` |
| `past_week`, `7d` | `past_week` |
| `past_month`, `30d` | `past_month` |

Example:

```text
GET /api/stock/NVDA/news?window=past_week
```

If no news is found, IMPERIA returns an empty `articles` list plus a warning. It does not fabricate stories.

